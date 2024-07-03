import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def predict_model(model, features):
    # Convert features to the required format for the model
    X = pd.DataFrame([features])
    X = pd.DataFrame(data=MinMaxScaler().fit_transform(X), columns=X.columns)
    prediction = model.predict(X)
    return prediction[0]