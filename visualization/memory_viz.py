import plotly.graph_objects as go
import numpy as np
import sqlite3
import json
from datetime import datetime

def load_embeddings():
    """
    Load embeddings from the memory database.
    Returns a tuple of (embeddings, texts, timestamps)
    """
    try:
        conn = sqlite3.connect('../test_clumps.db')
        cursor = conn.cursor()
        
        # Query memory embeddings, text and timestamps
        cursor.execute("""
            SELECT chunk_data 
            FROM clumps
            WHERE chunk_data IS NOT NULL
        """)
        
        results = cursor.fetchall()
        
        embeddings = []
        texts = []
        timestamps = []
        
        for row in results:
            chunk_data = json.loads(row[0])
            if 'embedding' in chunk_data:
                embeddings.append(chunk_data['embedding'])
                texts.append(chunk_data.get('text', 'No text'))
                # Timestamps may be in the chunk_data or use current time as fallback
                timestamps.append(datetime.now())
            
        return np.array(embeddings), texts, timestamps
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None, None, None
    finally:
        conn.close()

def create_3d_visualization(embeddings, texts, timestamps, output_file='memory_visualization.html'):
    """
    Create 3D scatter plot visualization of memory embeddings
    """
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings data available")
        return
        
    # Convert embeddings to 3D using first three dimensions
    x = embeddings[:, 0]
    y = embeddings[:, 1] 
    z = embeddings[:, 2]
    
    # Create color scale based on timestamp recency
    latest_ts = max(timestamps)
    colors = [(ts - min(timestamps)).total_seconds() for ts in timestamps]
    
    # Create the 3D scatter plot
    fig = go.Figure(data=[go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=6,
            color=colors,
            colorscale='Viridis',
            opacity=0.8
        ),
        text=[f"Text: {t}<br>Time: {ts}" for t, ts in zip(texts, timestamps)],
        hoverinfo='text'
    )])
    
    # Update the layout
    fig.update_layout(
        title='Memory Embeddings Visualization',
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z'
        ),
        width=1000,
        height=800
    )
    
    # Save to HTML file
    try:
        fig.write_html(output_file)
        print(f"Visualization saved to {output_file}")
    except Exception as e:
        print(f"Error saving visualization: {e}")

if __name__ == "__main__":
    # Load data
    print("Loading memory embeddings...")
    embeddings, texts, timestamps = load_embeddings()
    
    # Create visualization
    print("Creating visualization...")
    create_3d_visualization(embeddings, texts, timestamps)

