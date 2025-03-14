# Import necessary libraries
import os
import pandas as pd
import torch
from torch.utils.data import DataLoader
from transformers import T5ForConditionalGeneration, T5Tokenizer
from Dataset import AmplitudeDataset
import argparse

from model_titans import TitansModel
from utils import evaluate_titans_sequence_accuracy, plot_training_history, train_titans_model


def input_args():
    parser = argparse.ArgumentParser(description='Train a T5 model for amplitude data')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size for training')
    parser.add_argument('--num_epochs', type=int, default=2, help='Number of epochs for training')
    parser.add_argument('--lr', type=float, default=5e-5, help='Learning rate for training')
    #parser.add_argument('--max_length', type=int, default=512, help='Maximum input length for the model')
    parser.add_argument('--model_dir', type=str, default='model_titans', help='Directory to save the trained model')
    parser.add_argument('--source_dir', type=str, default='data', help='Directory containing the data files')
    return parser.parse_args()

def main():
    
    # Parse input arguments
    args = input_args()
    
    # Load the data back from the pickle file
    source_dir = args.source_dir
    train_df = pd.read_pickle(os.path.join(source_dir, "train.pkl"))
    val_df = pd.read_pickle(os.path.join(source_dir, "val.pkl"))
    test_df = pd.read_pickle(os.path.join(source_dir, "test.pkl"))
    
    
    # Initialize tokenizer and model
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    model = T5ForConditionalGeneration.from_pretrained('t5-small')

    # Add special tokens for mathematical expressions
    special_tokens = ['*', '/', '+', '-', '^', '(', ')', '{', '}', '_', 'gamma', 'sigma', 'e^2']
    tokenizer.add_tokens(special_tokens)
    tokenizer.add_tokens(['[START]'])
    model.resize_token_embeddings(len(tokenizer))
    print(f"Vocabulary size after adding special tokens: {len(tokenizer)}")
    print(f"Special tokens added: {special_tokens}")
    
    # Create datasets
    train_dataset = AmplitudeDataset(
        train_df['tokenized_amplitude'].tolist(),
        train_df['tokenized_squared_amplitude'].tolist(),
        tokenizer
    )

    val_dataset = AmplitudeDataset(
        val_df['tokenized_amplitude'].tolist(),
        val_df['tokenized_squared_amplitude'].tolist(),
        tokenizer
    )

    test_dataset = AmplitudeDataset(
        test_df['tokenized_amplitude'].tolist(),
        test_df['tokenized_squared_amplitude'].tolist(),
        tokenizer
    )

    # Create data loaders
    batch_size = args.batch_size
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    print(f"Number of training batches: {len(train_loader)}")
    print(f"Number of validation batches: {len(val_loader)}")
    print(f"Number of test batches: {len(test_loader)}")
    
    # Train the model
    # Initialize TITANS model
    vocab_size = len(tokenizer)
    titans_model = TitansModel(vocab_size=vocab_size, start_token_id = tokenizer.convert_tokens_to_ids('[START]'))
    
    # Set epochs to a small number for initial testing, increase for better results
    trained_titans_model, history = train_titans_model(titans_model, tokenizer, train_loader, val_loader, epochs=args.num_epochs, lr=args.lr)

    # Plot training history
    os.makedirs(args.model_dir, exist_ok=True)
    plot_training_history(history, os.path.join(args.model_dir, 'training_history.png'))
    
    # Evaluate on test set
    test_accuracy, predictions, targets = evaluate_titans_sequence_accuracy(trained_titans_model, tokenizer, test_loader)
    print(f"Test sequence accuracy: {test_accuracy:.4f}")

    # Display some example predictions
    print("\nSample predictions vs targets:")
    for i, (pred, target) in enumerate(zip(predictions, targets)):
        print(f"\nExample {i+1}:")
        print(f"Prediction: {pred[:100]}..." if len(pred) > 100 else f"Prediction: {pred}")
        print(f"Target: {target[:100]}..." if len(target) > 100 else f"Target: {target}")
        print(f"Correct: {pred == target}")

    # Save the model and tokenizer
    torch.save(trained_titans_model.state_dict(), os.path.join(args.model_dir, 'amplitude_model.pth'))
    tokenizer.save_pretrained(os.path.join(args.model_dir, 'amplitude_tokenizer'))

    print("Model and tokenizer saved successfully!")
    
if __name__ == "__main__":
    main()