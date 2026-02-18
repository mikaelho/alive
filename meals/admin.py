"""Django admin configuration for meals models."""

from django.contrib import admin

from .models import FamilyMember, Ingredient, Tag, Recipe, RecipeIngredient, Meal, MealRating


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 3


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    search_fields = ['title', 'description']
    inlines = [RecipeIngredientInline]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['date', 'meal_type', 'recipe']
    list_filter = ['meal_type', 'date']
    date_hierarchy = 'date'


@admin.register(MealRating)
class MealRatingAdmin(admin.ModelAdmin):
    list_display = ['family_member', 'recipe', 'liked']
    list_filter = ['liked', 'family_member']
