#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int query(const vector<int>& v) {
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    int N;
    cin >> N;
    int total = 2 * N;
    
    vector<int> gender(total + 1, 0); // 0 unknown, 1 X, 2 Y
    vector<int> X, Y;
    
    // Find first pair with result 1
    int a = -1, b = -1;
    for (int i = 1; i <= total && a == -1; ++i) {
        for (int j = i + 1; j <= total && a == -1; ++j) {
            vector<int> v = {i, j};
            int res = query(v);
            if (res == 1) {
                a = i;
                b = j;
                gender[i] = 1;
                gender[j] = 2;
                X.push_back(i);
                Y.push_back(j);
                break;
            }
        }
    }
    
    // Assign other chameleons using known X and Y
    for (int i = 1; i <= total; ++i) {
        if (gender[i] != 0) continue;
        bool found = false;
        for (int x : X) {
            vector<int> v = {i, x};
            int res = query(v);
            if (res == 1) {
                gender[i] = 2;
                Y.push_back(i);
                found = true;
                break;
            }
        }
        if (found) continue;
        for (int y : Y) {
            vector<int> v = {i, y};
            int res = query(v);
            if (res == 1) {
                gender[i] = 1;
                X.push_back(i);
                found = true;
                break;
            }
        }
        if (found) continue;
        // leave unknown for now
    }
    
    // Process remaining unknown chameleons
    vector<int> unknown;
    for (int i = 1; i <= total; ++i) {
        if (gender[i] == 0) unknown.push_back(i);
    }
    while (!unknown.empty()) {
        int u = unknown.back();
        unknown.pop_back();
        bool done = false;
        for (size_t idx = 0; idx < unknown.size(); ++idx) {
            int v = unknown[idx];
            vector<int> w = {u, v};
            int res = query(w);
            if (res == 1) {
                // Determine genders using known X
                int x0 = X[0];
                vector<int> w2 = {u, x0};
                int res2 = query(w2);
                if (res2 == 1) {
                    gender[u] = 2;
                    gender[v] = 1;
                    Y.push_back(u);
                    X.push_back(v);
                } else {
                    gender[u] = 1;
                    gender[v] = 2;
                    X.push_back(u);
                    Y.push_back(v);
                }
                unknown.erase(unknown.begin() + idx);
                done = true;
                break;
            }
        }
        if (!done) {
            // Fallback: assign to X
            gender[u] = 1;
            X.push_back(u);
        }
    }
    
    // Pair X and Y by same color (assuming query result 1 indicates same color)
    vector<bool> usedY(Y.size(), false);
    for (int x : X) {
        bool paired = false;
        for (size_t j = 0; j < Y.size(); ++j) {
            if (usedY[j]) continue;
            int y = Y[j];
            vector<int> v = {x, y};
            int res = query(v);
            if (res == 1) {
                cout << "Answer " << x << " " << y << endl;
                usedY[j] = true;
                paired = true;
                break;
            }
        }
        if (!paired) {
            // Fallback: pair with first unused Y
            for (size_t j = 0; j < Y.size(); ++j) {
                if (!usedY[j]) {
                    cout << "Answer " << x << " " << Y[j] << endl;
                    usedY[j] = true;
                    break;
                }
            }
        }
    }
    
    return 0;
}