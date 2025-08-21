"""
Embedding-based content scoring and similarity analysis.

This module provides advanced content quality assessment using OpenAI embeddings
and machine learning techniques. It enables sophisticated analysis of content
similarity, alignment, and semantic coherence across different content formats.

Key features:
- Semantic similarity analysis using state-of-the-art embeddings
- Content alignment scoring between original and generated posts
- Multi-dimensional quality assessment with cosine similarity
- Content gap detection to identify missing key concepts
- Cross-platform consistency analysis
- Quality scoring with statistical confidence metrics

Why embedding analysis matters:
- Ensures generated content maintains semantic coherence with source material
- Enables quality-based content ranking and selection
- Detects potential content drift or hallucination
- Provides quantitative metrics for content review processes
- Supports automated quality assurance workflows
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import tiktoken

from ..config import config
from ..models import KeyPoint, PlatformPost


class ContentEmbeddingAnalyzer:
    """
    Analyzes content using OpenAI embeddings for similarity and quality scoring.
    
    This class provides comprehensive content analysis capabilities using
    state-of-the-art embedding models. It enables semantic understanding
    beyond simple keyword matching.
    
    Why use embeddings for content analysis:
    - Captures semantic meaning beyond surface-level text matching
    - Robust to paraphrasing and different wording
    - Enables comparison across different content formats
    - Provides quantitative similarity metrics
    - Supports automated content quality assessment
    """
    
    def __init__(self):
        # Initialize OpenAI client for embedding generation
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Use smaller embedding model for cost efficiency while maintaining quality
        # text-embedding-3-small provides excellent performance for content similarity
        self.embedding_model = "text-embedding-3-small"
        
        # Initialize tokenizer for text length management
        # Important for staying within embedding model limits
        self.encoding = tiktoken.encoding_for_model("gpt-4o")
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text content."""
        try:
            # Truncate text if too long (max 8192 tokens for embedding model)
            tokens = self.encoding.encode(text)
            if len(tokens) > 8000:
                text = self.encoding.decode(tokens[:8000])
            
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return [0.0] * 1536  # Default dimension for text-embedding-3-small
    
    def calculate_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        try:
            embedding1 = np.array(self.get_embedding(text1)).reshape(1, -1)
            embedding2 = np.array(self.get_embedding(text2)).reshape(1, -1)
            
            similarity = cosine_similarity(embedding1, embedding2)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"Similarity calculation failed: {e}")
            return 0.0
    
    def score_content_alignment(self, original_text: str, key_points: List[KeyPoint], 
                               platform_posts: Dict[str, PlatformPost]) -> Dict[str, float]:
        """Score how well platform posts align with original content and key insights."""
        original_embedding = np.array(self.get_embedding(original_text)).reshape(1, -1)
        key_points_text = " ".join([kp.text for kp in key_points])
        key_points_embedding = np.array(self.get_embedding(key_points_text)).reshape(1, -1)
        
        alignment_scores = {}
        
        for platform, post in platform_posts.items():
            try:
                post_embedding = np.array(self.get_embedding(post.primary_text)).reshape(1, -1)
                
                # Calculate similarity with original content
                original_similarity = cosine_similarity(original_embedding, post_embedding)[0][0]
                
                # Calculate similarity with key points
                key_points_similarity = cosine_similarity(key_points_embedding, post_embedding)[0][0]
                
                # Weighted combination (key points more important for social media)
                alignment_score = 0.3 * original_similarity + 0.7 * key_points_similarity
                alignment_scores[platform] = float(alignment_score)
                
            except Exception as e:
                print(f"Alignment scoring failed for {platform}: {e}")
                alignment_scores[platform] = 0.5  # Default middle score
        
        return alignment_scores
    
    def analyze_content_clusters(self, texts: List[str], n_clusters: int = 3) -> Dict[str, List[int]]:
        """Cluster similar content pieces and identify themes."""
        if len(texts) < n_clusters:
            return {"cluster_0": list(range(len(texts)))}
        
        try:
            # Get embeddings for all texts
            embeddings = []
            for text in texts:
                embedding = self.get_embedding(text)
                embeddings.append(embedding)
            
            embeddings_array = np.array(embeddings)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_labels = kmeans.fit_predict(embeddings_array)
            
            # Group texts by cluster
            clusters = {}
            for i, label in enumerate(cluster_labels):
                cluster_key = f"cluster_{label}"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(i)
            
            return clusters
            
        except Exception as e:
            print(f"Content clustering failed: {e}")
            return {"cluster_0": list(range(len(texts)))}
    
    def calculate_content_quality_score(self, text: str, target_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate content quality based on embedding analysis and target metrics."""
        try:
            embedding = np.array(self.get_embedding(text)).reshape(1, -1)
            
            # Quality indicators based on embedding analysis
            quality_metrics = {}
            
            # 1. Content density (based on embedding magnitude)
            embedding_norm = np.linalg.norm(embedding)
            quality_metrics["content_density"] = min(float(embedding_norm / 10.0), 1.0)
            
            # 2. Semantic coherence (variance in embedding dimensions)
            embedding_variance = np.var(embedding)
            quality_metrics["semantic_coherence"] = max(0.0, min(1.0, float(1.0 - embedding_variance * 10)))
            
            # 3. Professional tone assessment (placeholder - could be enhanced with domain-specific embeddings)
            word_count = len(text.split())
            quality_metrics["professional_tone"] = min(1.0, word_count / 100.0) if word_count > 10 else 0.3
            
            # 4. Target audience alignment (if target metrics provided)
            if target_metrics:
                alignment_score = 0.0
                for metric, target_value in target_metrics.items():
                    if metric in quality_metrics:
                        difference = abs(quality_metrics[metric] - target_value)
                        alignment_score += max(0.0, 1.0 - difference)
                quality_metrics["target_alignment"] = alignment_score / len(target_metrics)
            
            # Overall quality score
            quality_metrics["overall_quality"] = np.mean(list(quality_metrics.values()))
            
            return quality_metrics
            
        except Exception as e:
            print(f"Quality scoring failed: {e}")
            return {"overall_quality": 0.5, "content_density": 0.5, "semantic_coherence": 0.5}
    
    def find_content_gaps(self, original_text: str, generated_posts: Dict[str, str]) -> Dict[str, List[str]]:
        """Identify content gaps between original text and generated posts."""
        try:
            original_embedding = np.array(self.get_embedding(original_text)).reshape(1, -1)
            
            gaps_analysis = {}
            
            for platform, post_text in generated_posts.items():
                post_embedding = np.array(self.get_embedding(post_text)).reshape(1, -1)
                
                # Calculate semantic distance
                similarity = cosine_similarity(original_embedding, post_embedding)[0][0]
                
                # Identify potential gaps based on similarity threshold
                gaps = []
                if similarity < 0.6:
                    gaps.append("Low semantic similarity to original content")
                if similarity < 0.4:
                    gaps.append("Significant content deviation detected")
                if len(post_text.split()) < 10:
                    gaps.append("Content may be too brief to capture key insights")
                
                # Check for missing key themes (simplified approach)
                original_words = set(original_text.lower().split())
                post_words = set(post_text.lower().split())
                
                important_words = {word for word in original_words if len(word) > 5}
                missing_important = important_words - post_words
                
                if missing_important and len(missing_important) > len(important_words) * 0.7:
                    gaps.append("Many important concepts from original text missing")
                
                gaps_analysis[platform] = gaps
            
            return gaps_analysis
            
        except Exception as e:
            print(f"Content gap analysis failed: {e}")
            return {platform: [] for platform in generated_posts.keys()}


def analyze_content_embeddings(original_text: str, key_points: List[KeyPoint], 
                             platform_posts: Dict[str, PlatformPost]) -> Dict[str, any]:
    """Main function to perform comprehensive embedding-based content analysis."""
    analyzer = ContentEmbeddingAnalyzer()
    
    try:
        # 1. Content alignment scoring
        alignment_scores = analyzer.score_content_alignment(original_text, key_points, platform_posts)
        
        # 2. Platform post quality assessment
        post_texts = {platform: post.primary_text for platform, post in platform_posts.items()}
        quality_scores = {}
        for platform, text in post_texts.items():
            quality_scores[platform] = analyzer.calculate_content_quality_score(text, {})
        
        # 3. Content gap analysis
        content_gaps = analyzer.find_content_gaps(original_text, post_texts)
        
        # 4. Cross-platform similarity analysis
        cross_platform_similarity = {}
        platforms = list(platform_posts.keys())
        for i, platform1 in enumerate(platforms):
            for platform2 in platforms[i+1:]:
                similarity = analyzer.calculate_content_similarity(
                    platform_posts[platform1].primary_text,
                    platform_posts[platform2].primary_text
                )
                cross_platform_similarity[f"{platform1}_vs_{platform2}"] = similarity
        
        # 5. Overall content coherence
        all_texts = [original_text] + [post.primary_text for post in platform_posts.values()]
        content_clusters = analyzer.analyze_content_clusters(all_texts)
        
        return {
            "alignment_scores": alignment_scores,
            "quality_scores": quality_scores,
            "content_gaps": content_gaps,
            "cross_platform_similarity": cross_platform_similarity,
            "content_clusters": content_clusters,
            "analysis_metadata": {
                "total_platforms": len(platform_posts),
                "original_text_length": len(original_text),
                "average_post_length": np.mean([len(post.primary_text) for post in platform_posts.values()])
            }
        }
        
    except Exception as e:
        print(f"Embedding analysis failed: {e}")
        return {
            "alignment_scores": {platform: 0.5 for platform in platform_posts.keys()},
            "quality_scores": {platform: {"overall_quality": 0.5} for platform in platform_posts.keys()},
            "content_gaps": {platform: [] for platform in platform_posts.keys()},
            "cross_platform_similarity": {},
            "content_clusters": {"cluster_0": list(range(len(platform_posts) + 1))},
            "analysis_metadata": {"error": str(e)}
        }