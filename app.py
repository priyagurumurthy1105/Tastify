import streamlit as st
import google.generativeai as genai
import json
import os

# Configure Google AI Studio API
# Note: User needs to set their API key as an environment variable or input it in the app
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyDHRTQGR9h7TGxh1XxEa_4yBBX0y_UKJGk"

if not API_KEY:
    st.error("Please set your Google AI Studio API key in environment variables or Streamlit secrets.")
    st.stop()

genai.configure(api_key=API_KEY)

# Initialize the model with explicit configuration
try:
    # First verify the API key by listing available models
    available_models = genai.list_models()
    model_names = [m.name for m in available_models]
    
    # Check if the model is available
    target_model = 'models/gemini-pro'
    if target_model not in model_names:
        st.error(f"Model '{target_model}' not found. Available models: {', '.join(model_names)}")
        st.stop()
    
    # Initialize the model
    model = genai.GenerativeModel('gemini-pro')
    
    # Test the model connection with a simple request
    try:
        response = model.generate_content("Test connection")
        if not response.text:
            st.error("Received empty response from the model. Check your API key and model access.")
            st.stop()
    except Exception as e:
        st.error(f"Failed to connect to the model. Error: {str(e)}")
        st.stop()
        
except Exception as e:
    st.error(f"Failed to initialize the model. Error: {str(e)}")
    st.error("Please check your API key and ensure it has access to the Gemini API.")
    st.stop()

def normalize_ingredients(ingredients_text):
    prompt = f"""
    Normalize the following user-provided ingredients into a clean, standardized list.
    Handle ambiguities, synonyms, and quantities. Output as JSON with key "normalized_ingredients" containing a list of strings.

    Ingredients: {ingredients_text}

    Example output:
    {{
        "normalized_ingredients": ["2 cups flour", "1 kg chicken breast", "3 onions"]
    }}
    """
    response = model.generate_content(prompt)
    try:
        result = json.loads(response.text.strip())
        return result.get("normalized_ingredients", [])
    except:
        return []

def suggest_dishes(normalized_ingredients):
    ingredients_str = ", ".join(normalized_ingredients)
    prompt = f"""
    Based on these ingredients: {ingredients_str}
    Suggest 3-5 dish ideas that can be made with these or similar ingredients.
    For each dish, provide a brief description and why it fits.
    Output as JSON with key "dishes" containing a list of objects, each with "name" and "description".

    Example output:
    {{
        "dishes": [
            {{
                "name": "Chicken Stir Fry",
                "description": "A quick stir fry using chicken and vegetables."
            }}
        ]
    }}
    """
    response = model.generate_content(prompt)
    try:
        result = json.loads(response.text.strip())
        return result.get("dishes", [])
    except:
        return []

def generate_recipe(dish_name, normalized_ingredients, servings=4, scale_factor=1.0, units="metric"):
    ingredients_str = ", ".join(normalized_ingredients)
    prompt = f"""
    Generate a full recipe for "{dish_name}" using these ingredients: {ingredients_str}
    Provide ingredients list, step-by-step instructions, prep time, cook time, and nutritional info if possible.
    Scale for {servings} servings, adjust quantities by factor {scale_factor}.
    Use {units} units (default metric, convert if needed).
    Include options for substitutions.
    Output as JSON with keys: "ingredients" (list of strings), "steps" (list of strings), "prep_time", "cook_time", "substitutions" (dict of ingredient: alternatives).

    Example output:
    {{
        "ingredients": ["500g chicken", "2 onions"],
        "steps": ["Chop onions", "Cook chicken"],
        "prep_time": "15 min",
        "cook_time": "30 min",
        "substitutions": {{"chicken": "tofu for vegetarian"}}
    }}
    """
    response = model.generate_content(prompt)
    try:
        result = json.loads(response.text.strip())
        return result
    except:
        return {}

def save_recipe(recipe, filename="saved_recipes.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            recipes = json.load(f)
    else:
        recipes = []
    recipes.append(recipe)
    with open(filename, "w") as f:
        json.dump(recipes, f, indent=4)

# Streamlit UI
st.title("AI-Powered Recipe Suggestion App")

ingredients_input = st.text_area("Enter your ingredients (comma-separated):", height=100)

if st.button("Normalize Ingredients"):
    if ingredients_input:
        normalized = normalize_ingredients(ingredients_input)
        st.session_state.normalized = normalized
        st.success("Ingredients normalized!")
        st.write("Normalized Ingredients:")
        for ing in normalized:
            st.write(f"- {ing}")
    else:
        st.error("Please enter some ingredients.")

if "normalized" in st.session_state and st.session_state.normalized:
    if st.button("Suggest Dishes"):
        dishes = suggest_dishes(st.session_state.normalized)
        st.session_state.dishes = dishes
        st.success("Dish suggestions generated!")
        st.write("Suggested Dishes:")
        for i, dish in enumerate(dishes):
            st.write(f"{i+1}. **{dish['name']}**: {dish['description']}")

    if "dishes" in st.session_state and st.session_state.dishes:
        dish_options = [dish["name"] for dish in st.session_state.dishes]
        selected_dish = st.selectbox("Select a dish to generate recipe:", dish_options)

        servings = st.number_input("Number of servings:", min_value=1, value=4)
        scale_factor = st.slider("Scale factor:", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
        units = st.selectbox("Units:", ["metric", "imperial"])

        if st.button("Generate Recipe"):
            recipe = generate_recipe(selected_dish, st.session_state.normalized, servings, scale_factor, units)
            if recipe:
                st.session_state.recipe = recipe
                st.success("Recipe generated!")
                st.subheader(f"Recipe for {selected_dish}")
                st.write("**Ingredients:**")
                for ing in recipe.get("ingredients", []):
                    st.write(f"- {ing}")
                st.write("**Steps:**")
                for step in recipe.get("steps", []):
                    st.write(f"- {step}")
                st.write(f"**Prep Time:** {recipe.get('prep_time', 'N/A')}")
                st.write(f"**Cook Time:** {recipe.get('cook_time', 'N/A')}")
                st.write("**Substitutions:**")
                subs = recipe.get("substitutions", {})
                for orig, alt in subs.items():
                    st.write(f"- {orig}: {alt}")

                if st.button("Save Recipe"):
                    save_recipe(recipe)
                    st.success("Recipe saved to saved_recipes.json!")
            else:
                st.error("Failed to generate recipe. Please try again.")
