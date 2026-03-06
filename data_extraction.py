import pandas as pd
from rdkit import Chem # type: ignore
from rdkit.Chem import Descriptors # type: ignore

def property_split(df, smiles_col='SMILES', label_col='Answer', property_type='MW', train_frac=0.8):
    """
    Separe training and test set
    """
    df_split = df.copy()
    
    def calculate_property(smiles):
        mol = Chem.MolFromSmiles(str(smiles))
        if mol is None: return None
        return Descriptors.MolWt(mol) if property_type == 'MW' else Descriptors.MolLogP(mol)

    df_split[property_type] = df_split[smiles_col].apply(calculate_property)
    df_split = df_split.dropna(subset=[property_type])
    
    df_split = df_split.sort_values(by=property_type, ascending=True).reset_index(drop=True)
    split_index = int(len(df_split) * train_frac)
    
    train_df = df_split.iloc[:split_index].copy()
    test_df = df_split.iloc[split_index:].copy()
    
    return train_df, test_df


def clean_and_format_dataset(df):
    df_clean = df[['TargetMolecule', 'Answer']].copy()
    
    # Renommer pour un format standard
    df_clean = df_clean.rename(columns={
        'TargetMolecule': 'SMILES',
        'Answer': 'Label'
    })
    
    # Convertir les labels texte en nombres
    df_clean['Label'] = df_clean['Label'].replace({
        '<boolean>No</boolean>': 0, 
        '<boolean>Yes</boolean>': 1
    })
    
    # Supprimer les lignes incomplètes et les doublons de molécules
    df_clean = df_clean.dropna(subset=['SMILES', 'Label'])
    
    return df_clean

def main():
    df = pd.read_parquet("hf://datasets/molvision/BACE-V-SMILES-0/data/train-00000-of-00001.parquet")
    df = df.drop_duplicates(subset=['TargetMolecule']).reset_index(drop=True)
    
    train_df, test_df = property_split(df, smiles_col='TargetMolecule', label_col='Answer', property_type='MW')
    
    train_df_clean = clean_and_format_dataset(train_df)
    test_df_clean = clean_and_format_dataset(test_df)
    
    train_df_clean.to_csv("train.csv")
    test_df_clean.to_csv("test.csv")

if __name__ == "__main__":
    main()