"""Django models for the family meals application."""

from django.db import models

from alive import AliveMixin, AliveConf, TagFieldConf


class FamilyMember(models.Model, AliveMixin):
    """A family member who eats meals and has preferences."""

    alive = AliveConf(
        fields=("name",),
        editable_fields=("name",),
        title_field="name",
    )

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model, AliveMixin):
    """An ingredient used in recipes."""

    alive = AliveConf(
        fields=("name",),
        editable_fields=("name",),
        title_field="name",
    )

    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model, AliveMixin):
    """A tag for categorizing recipes and meals (e.g., 'quick', 'vegetarian')."""

    alive = AliveConf(
        fields=("name",),
        title_field="name",
    )

    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model, AliveMixin):
    """A recipe with ingredients and instructions."""

    alive = AliveConf(
        fields=("title", "description"),
        editable_fields=("title", "description"),
        title_field="title",
        dive_to=("ingredients",),
        tag_fields=(
            TagFieldConf(field_name="tags"),
        ),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    """Links a recipe to an ingredient with quantity."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
    )
    quantity = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ['recipe', 'ingredient']

    def __str__(self):
        if self.quantity:
            return f"{self.quantity} {self.ingredient.name}"
        return self.ingredient.name


class Meal(models.Model, AliveMixin):
    """A planned meal for a specific date and time."""

    MEAL_TYPES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]

    alive = AliveConf(
        fields=("date", "meal_type", "recipe"),
        title_field="meal_type",
        tag_fields=(
            TagFieldConf(field_name="tags", scope_path="recipe"),
        ),
    )

    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='meals',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='meals',
    )

    class Meta:
        ordering = ['date', 'meal_type']
        unique_together = ['date', 'meal_type']

    def __str__(self):
        return f"{self.date} {self.get_meal_type_display()}: {self.recipe.title}"


class MealRating(models.Model):
    """A family member's rating of a recipe."""

    family_member = models.ForeignKey(
        FamilyMember,
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    liked = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['family_member', 'recipe']

    def __str__(self):
        status = "likes" if self.liked else "dislikes"
        return f"{self.family_member.name} {status} {self.recipe.title}"
