#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    vector<int> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];
    
    if (accumulate(A.begin(), A.end(), 0) != accumulate(B.begin(), B.end(), 0)) {
        cout << "No\n";
        return 0;
    }
    
    if (A == B) {
        cout << "Yes\n0\n";
        return 0;
    }
    
    vector<pair<int, int>> ops;
    set<string> visited;
    auto get_key = [&](const vector<int>& v) {
        string s;
        for (int x : v) s += to_string(x) + " ";
        return s;
    };
    visited.insert(get_key(A));
    
    int cur_diff = 0;
    for (int i = 0; i < N; ++i) cur_diff += abs(A[i] - B[i]);
    
    const int MAX_STEPS = 10000;
    for (int step = 0; step < MAX_STEPS; ++step) {
        if (A == B) break;
        
        int best_diff = cur_diff;
        int best_i = -1, best_j = -1;
        vector<int> best_A;
        
        for (int i = 0; i < N; ++i) {
            for (int j = i + 1; j < N; ++j) {
                vector<int> newA = A;
                newA[i] = A[j] - 1;
                newA[j] = A[i] + 1;
                string key = get_key(newA);
                if (visited.count(key)) continue;
                
                int diff = 0;
                for (int k = 0; k < N; ++k) diff += abs(newA[k] - B[k]);
                if (diff < best_diff) {
                    best_diff = diff;
                    best_i = i;
                    best_j = j;
                    best_A = move(newA);
                }
            }
        }
        
        if (best_i == -1) {
            cout << "No\n";
            return 0;
        }
        
        A = best_A;
        visited.insert(get_key(A));
        ops.emplace_back(best_i, best_j);
        cur_diff = best_diff;
    }
    
    if (A == B) {
        cout << "Yes\n";
        cout << ops.size() << "\n";
        for (auto [i, j] : ops)
            cout << i + 1 << " " << j + 1 << "\n";
    } else {
        cout << "No\n";
    }
    
    return 0;
}