import sys
import argparse
import logging
from processing.terrain_generator import TerrainRenderer

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("==================================================================")
    print("Welcome to EstateMind Generative AI: Custom Property Visualization")
    print("==================================================================")
    
    parser = argparse.ArgumentParser(description='Generate a property render from an empty terrain or basic house.')
    parser.add_argument('image_path', nargs='?', default="downloads/images/sample_terrain.jpg", help='Path to the original image')
    parser.add_argument('--type', type=str, default="modern luxury villa", 
                        help='What kind of building? e.g., "small cozy house", "apartment complex", "modern luxury villa", "industrial warehouse"')
    parser.add_argument('--style', type=str, default="realistic 8k render", 
                        help='What style? e.g., "3D architectural render", "cinematic lighting", "high definition photo"')
    parser.add_argument('--extra', type=str, default="with a front pool and glass windows", 
                        help='Any extra details to add?')
    
    args = parser.parse_args()
    
    # Construct a highly detailed prompt based on the user's choices
    prompt = f"turn this into a {args.style} of a {args.type} {args.extra}"
    
    print(f"\n🧠 Prompt that will be used: '{prompt}'")
    print(f"📸 Image source: {args.image_path}")
    print("------------------------------------------------------------------")
    
    renderer = TerrainRenderer()
    
    # Generate the requested structure
    output_name = f"future_{args.type.replace(' ', '_')}_render.jpg"
    
    output = renderer.generate_property_render(
        original_image_path=args.image_path,
        prompt=prompt,
        output_name=output_name
    )
    
    if output:
        print(f"\n🎉 Success! You can view your new 3D render at: {output}")
