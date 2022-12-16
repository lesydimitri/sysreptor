from typing import Iterable
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from reportcreator_api.pentests.customfields.utils import HandleUndefinedFieldsOptions, ensure_defined_structure

from reportcreator_api.pentests.models import FindingTemplate, PentestFinding, PentestProject, ProjectType, ReportSection, \
    SourceEnum, UploadedAsset, UploadedImage, ProjectMemberInfo
from reportcreator_api.pentests.serializers import ProjectMemberInfoSerializer
from reportcreator_api.users.models import PentestUser
from reportcreator_api.users.serializers import RelatedUserSerializer
from reportcreator_api.utils.files import compress_image
from reportcreator_api.utils.logging import log_timing


class ExportImportSerializer(serializers.ModelSerializer):
    def perform_import(self):
        return self.create(self.validated_data.copy())

    def export(self):
        return self.data

    def export_files(self) -> Iterable[tuple[str, File]]:
        return []


class FormatField(serializers.Field):
    def __init__(self, format):
        self.format = format
        self.default_validators = [self._validate_format]
        super().__init__()

    def _validate_format(self, v):
        if v != self.format:
            raise serializers.ValidationError(f'Invalid format: expected "{self.format}" got "{v}"')
        else:
            raise serializers.SkipField()

    def get_attribute(self, instance):
        return self.format

    def to_representation(self, value):
        return value

    def to_internal_value(self, value):
        return value


class UserIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = PentestUser
        fields = ['id']


class RelatedUserIdExportImportSerializer(RelatedUserSerializer):
    def __init__(self, **kwargs):
        super().__init__(user_serializer=UserIdSerializer, **{'required': False, 'allow_null': True, 'default': None} | kwargs)

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except PentestUser.DoesNotExist:
            # If user does not exit: ignore
            raise serializers.SkipField()


class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PentestUser
        fields = [
            'id', 'email', 'phone', 'mobile',
            'name', 'title_before', 'first_name', 'middle_name', 'last_name', 'title_after', 
        ]
        extra_kwargs = {'id': {'read_only': False}}


class RelatedUserDataExportImportSerializer(ProjectMemberInfoSerializer):
    def __init__(self, **kwargs):
        super().__init__(user_serializer=UserDataSerializer, **kwargs)
    
    def to_internal_value(self, data):
        try:
            print(f'{self.context=}')
            return ProjectMemberInfo(**super().to_internal_value(data))
        except PentestUser.DoesNotExist:
            return data


class OptionalPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        super().__init__(**{'required': False, 'allow_null': True, 'default': None} | kwargs)
    
    def to_internal_value(self, data):
        if data is None:
            raise serializers.SkipField()
        try:
            return self.get_queryset().get(pk=data)
        except ObjectDoesNotExist:
            raise serializers.SkipField()


class FindingTemplateExportImportSerializer(ExportImportSerializer):
    format = FormatField('templates/v1')

    data = serializers.DictField(source='data_all')

    class Meta:
        model = FindingTemplate
        fields = ['format', 'id', 'created', 'updated', 'tags', 'language', 'status', 'data']
        extra_kwargs = {'id': {'read_only': True}, 'created': {'read_only': False}}
    
    def create(self, validated_data):
        data = validated_data.pop('data_all', {})
        template = FindingTemplate(**{
            'source': SourceEnum.IMPORTED,
        } | validated_data)
        template.update_data(data)
        template.save()
        return template


class FileListExportImportSerializer(serializers.ListSerializer):
    def export_files(self):
        for e in self.instance:
            self.child.instance = e
            yield from self.child.export_files()

    def extract_file(self, name):
        return compress_image(self.context['archive'].extractfile(self.child.get_path_in_archive(name)))[0]

    def create(self, validated_data):
        child_model_class = self.child.Meta.model
        objs = [
            child_model_class(**attrs | {
            'file': File(
                file=self.extract_file(attrs['name']), 
                name=attrs['name']), 
            'linked_object': self.child.get_linked_object()
        }) for attrs in validated_data]

        child_model_class.objects.bulk_create(objs)
        self.context['storage_files'].extend(map(lambda o: o.file, objs))
        return objs


class FileExportImportSerializer(ExportImportSerializer):
    class Meta:
        fields = ['id', 'created', 'updated', 'name']
        extra_kwargs = {'id': {'read_only': True}, 'created': {'read_only': False}}
        list_serializer_class = FileListExportImportSerializer

    def validate_name(self, name):
        if '/' in name or '\\' in name or '\x00' in name:
            raise serializers.ValidationError(f'Invalid filename: {name}')
        return name

    def get_linked_object(self):
        pass

    def get_path_in_archive(self, name):
        pass

    def export_files(self) -> Iterable[tuple[str, File]]:
        yield self.get_path_in_archive(self.instance.name), self.instance.file


class UploadedImageExportImportSerializer(FileExportImportSerializer):
    class Meta(FileExportImportSerializer.Meta):
        model = UploadedImage

    def get_linked_object(self):
        return self.context['project']
    
    def get_path_in_archive(self, name):
        # Get ID of old project_type from archive
        return str(self.context.get('project_id') or self.get_linked_object().id) + '-images/' + name


class UploadedAssetExportImportSerializer(FileExportImportSerializer):
    class Meta(FileExportImportSerializer.Meta):
        model = UploadedAsset
    
    def get_linked_object(self):
        return self.context['project_type']
    
    def get_path_in_archive(self, name):
        # Get ID of old project_type from archive
        return str(self.context.get('project_type_id') or self.get_linked_object().id) + '-assets/' + name


class ProjectTypeExportImportSerializer(ExportImportSerializer):
    format = FormatField('projecttypes/v1')
    assets = UploadedAssetExportImportSerializer(many=True)

    class Meta:
        model = ProjectType
        fields = [
            'format', 'id', 'created', 'updated', 'name', 'language', 
            'report_fields', 'report_sections', 'finding_fields', 'finding_field_order', 
            'report_template', 'report_styles', 'report_preview_data', 
            'assets'
        ]
        extra_kwargs = {'id': {'read_only': False}, 'created': {'read_only': False}}

    def export_files(self) -> Iterable[tuple[str, File]]:
        af = self.fields['assets']
        self.context.update({'project_type': self.instance})
        af.instance = list(af.get_attribute(self.instance).all())
        yield from af.export_files()

    def create(self, validated_data):
        old_id = validated_data.pop('id')
        assets = validated_data.pop('assets', [])
        project_type = super().create({
            'source': SourceEnum.IMPORTED,
        } | validated_data)
        self.context.update({'project_type': project_type, 'project_type_id': old_id})
        self.fields['assets'].create(assets)
        return project_type


class PentestFindingExportImportSerializer(ExportImportSerializer):
    id = serializers.UUIDField(source='finding_id')
    assignee = RelatedUserIdExportImportSerializer()
    template = OptionalPrimaryKeyRelatedField(queryset=FindingTemplate.objects.all())
    data = serializers.DictField(source='data_all')

    class Meta:
        model = PentestFinding
        fields = [
            'id', 'created', 'updated', 'assignee', 'status', 'template', 'data',
        ]
        extra_kwargs = {'created': {'read_only': False}}

    def create(self, validated_data):
        project = self.context['project']
        data = validated_data.pop('data_all', {})
        finding = PentestFinding(**{
            'project': project,
        } | validated_data)
        finding.update_data(ensure_defined_structure(
            value=data,
            definition=project.project_type.finding_fields_obj,
            handle_undefined=HandleUndefinedFieldsOptions.FILL_NONE,
            include_undefined=True)
        )
        finding.save()
        return finding


class ReportSectionExportImportSerializer(ExportImportSerializer):
    id = serializers.CharField(source='section_id')
    assignee = RelatedUserIdExportImportSerializer()

    class Meta:
        model = ReportSection
        fields = [
            'id', 'created', 'updated', 'assignee', 'status',
        ]
        extra_kwargs = {'created': {'read_only': False}}


class PentestProjectExportImportSerializer(ExportImportSerializer):
    format = FormatField('projects/v1')
    members = RelatedUserDataExportImportSerializer(many=True, required=False)
    pentesters = RelatedUserDataExportImportSerializer(many=True, required=False)
    project_type = ProjectTypeExportImportSerializer()
    report_data = serializers.DictField(source='data_all')
    sections = ReportSectionExportImportSerializer(many=True)
    findings = PentestFindingExportImportSerializer(many=True)
    images = UploadedImageExportImportSerializer(many=True)

    class Meta:
        model = PentestProject
        fields = [
            'format', 'id', 'created', 'updated', 'name', 'language', 
            'members', 'pentesters', 'project_type', 
            'report_data', 'sections', 'findings', 'images',

        ]
        extra_kwargs = {'id': {'read_only': False}, 'created': {'read_only': False}}

    def export_files(self) -> Iterable[tuple[str, File]]:
        self.fields['project_type'].instance = self.instance.project_type
        yield from self.fields['project_type'].export_files()

        ff = self.fields['images']
        self.context.update({'project': self.instance})
        ff.instance = list(ff.get_attribute(self.instance).all())
        yield from ff.export_files()
    
    def create(self, validated_data):
        old_id = validated_data.pop('id')
        members = validated_data.pop('members', validated_data.pop('pentesters', []))
        project_type_data = validated_data.pop('project_type', {})
        sections = validated_data.pop('sections', [])
        findings = validated_data.pop('findings', [])
        report_data = validated_data.pop('data_all', {})
        images_data = validated_data.pop('images', [])

        project_type = self.fields['project_type'].create(project_type_data | {
            'source': SourceEnum.IMPORTED_DEPENDENCY,
        })
        project = super().create(validated_data | {
            'project_type': project_type,
            'imported_members': list(filter(lambda u: isinstance(u, dict), members)),
            'source': SourceEnum.IMPORTED,
            'custom_fields': ensure_defined_structure(
                value=report_data,
                definition=project_type.report_fields_obj,
                handle_undefined=HandleUndefinedFieldsOptions.FILL_NONE,
                include_undefined=True
            ),    
        })
        project_type.linked_project = project
        project_type.save()

        member_infos = list(filter(lambda u: isinstance(u, ProjectMemberInfo), members))
        for mi in member_infos:
            mi.project = project
        ProjectMemberInfo.objects.bulk_create(member_infos)

        self.context.update({'project': project, 'project_id': old_id})

        for section in project.sections.all():
            if section_data := next(filter(lambda s: s.get('section_id') == section.section_id, sections), None):
                self.fields['sections'].child.update(section, section_data)

        self.fields['findings'].create(findings)
        self.fields['images'].create(images_data)

        return project

