from rest_framework import serializers
from .models import User, UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password' , None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['email', 'password']


class UserProfileSerializer(serializers.ModelSerializer):
    # skills_list = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'bio', 'phone','learning_streak', 'average_accuracy', 'average_time_per_question',
            'avg_difficulty','created_at', 'modified_at'
        ]
        read_only_fields = ['created_at', 'modified_at']



    def validate_phone(self, value):
        if value and len(value.replace(' ', '').replace('-', '')) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value




class UserWithProfileSerializer(serializers.ModelSerializer):
    """Extended user serializer that includes profile data"""
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'profile']  # Adjust fields based on your User model


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile data"""

    class Meta:
        model = UserProfile
        fields = [
            'bio', 'phone', #more fields as needed
        ]

    """def update(self, instance, validated_data):
        # Handle skills_list separately
        skills_list = validated_data.pop('skills_list', None)
        if skills_list is not None:
            instance.set_skills_list(skills_list)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance"""


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs

    def validate_new_password(self, value):
        # Add password strength validation
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if value.isdigit():
            raise serializers.ValidationError("Password cannot be entirely numeric.")
        return value
    
class SerializeUserInfo(serializers.Serializer):
    primary_goal = serializers.CharField(max_length=255)
    daily_target_time = serializers.IntegerField(required=False, allow_null=True)
    interests = serializers.JSONField(required=False, allow_null=True)
    