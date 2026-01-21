#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<int>> cards(n);
    for (int i = 0; i < n; ++i) {
        cards[i].resize(n);
        for (int j = 0; j < n; ++j) cin >> cards[i][j];
    }
    
    auto allSolid = [&](const vector<vector<int>>& c) -> bool {
        for (int i = 0; i < n; ++i) {
            for (int v : c[i]) if (v != i + 1) return false;
        }
        return true;
    };
    
    int Kmax = n * n - n;
    vector<vector<int>> ops;
    ops.reserve(Kmax);
    
    for (int step = 0; step < Kmax; ++step) {
        if (allSolid(cards)) break;
        
        vector<int> chooseVal(n);
        vector<int> chooseIdx(n);
        
        for (int i = 0; i < n; ++i) {
            int bestIdx = -1;
            int bestDist = -1;
            for (int idx = 0; idx < (int)cards[i].size(); ++idx) {
                int v = cards[i][idx];
                int dist = (v - (i + 1) + n) % n;
                if (dist > 0 && dist > bestDist) {
                    bestDist = dist;
                    bestIdx = idx;
                }
            }
            if (bestIdx == -1) bestIdx = 0;
            chooseIdx[i] = bestIdx;
            chooseVal[i] = cards[i][bestIdx];
        }
        
        ops.push_back(chooseVal);
        
        vector<vector<int>> newCards(n);
        for (int i = 0; i < n; ++i) {
            int remIdx = chooseIdx[i];
            for (int idx = 0; idx < (int)cards[i].size(); ++idx) {
                if (idx == remIdx) continue;
                newCards[i].push_back(cards[i][idx]);
            }
        }
        for (int i = 0; i < n; ++i) {
            int from = (i - 1 + n) % n;
            newCards[i].push_back(chooseVal[from]);
        }
        cards.swap(newCards);
    }
    
    cout << ops.size() << "\n";
    for (auto &row : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << row[i];
        }
        cout << "\n";
    }
    
    return 0;
}