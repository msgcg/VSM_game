from django.contrib import admin
from .models import (
    Competency,
    ConductorProfile,
    ConductorCompetencyScore,
    Achievement,
    ConductorAchievement,
    Scenario,
    ScenarioNode,
    ScenarioChoice,
    TrainingSession,
)


class ConductorCompetencyScoreInline(admin.TabularInline):
    model = ConductorCompetencyScore
    extra = 0


class ConductorAchievementInline(admin.TabularInline):
    model = ConductorAchievement
    extra = 0


@admin.register(ConductorProfile)
class ConductorProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'badge_number', 'rank', 'level', 'experience_points', 'loyalty_rating', 'safety_rating', 'shifts_completed')
    list_filter = ('rank', 'depot')
    search_fields = ('full_name', 'badge_number')
    inlines = [ConductorCompetencyScoreInline, ConductorAchievementInline]


class ScenarioChoiceInline(admin.StackedInline):
    model = ScenarioChoice
    extra = 1


@admin.register(ScenarioNode)
class ScenarioNodeAdmin(admin.ModelAdmin):
    list_display = ('title', 'scenario', 'node_key', 'character_name', 'character_mood', 'time_limit_seconds', 'is_terminal', 'is_success')
    list_filter = ('scenario', 'is_terminal', 'is_success')
    search_fields = ('title', 'dialogue_text', 'node_key')
    inlines = [ScenarioChoiceInline]


class ScenarioNodeInline(admin.TabularInline):
    model = ScenarioNode
    extra = 0
    fields = ('node_key', 'title', 'character_name', 'time_limit_seconds', 'is_terminal', 'is_success')


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'difficulty', 'train_speed', 'location_name', 'base_xp', 'is_active', 'order')
    list_filter = ('category', 'difficulty', 'is_active')
    search_fields = ('title', 'description', 'briefing')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ScenarioNodeInline]


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'rarity', 'xp_reward', 'badge_color')
    list_filter = ('rarity',)
    search_fields = ('title', 'description')


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'color')
    search_fields = ('title', 'description')


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('conductor', 'scenario', 'status', 'final_score', 'earned_xp', 'current_loyalty', 'current_safety', 'started_at', 'completed_at')
    list_filter = ('status', 'is_success')
    search_fields = ('conductor__full_name', 'scenario__title')
