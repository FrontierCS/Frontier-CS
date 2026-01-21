#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<int> Jx(M), Jy(M);
    for (int i = 0; i < M; ++i) {
        cin >> Jx[i] >> Jy[i];
    }
    
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;
    
    set<int> wrong;
    for (int i = 0; i < N; ++i) if (S[i] != i) wrong.insert(i);
    
    auto update_wrong = [&](int idx) {
        if (idx < 0 || idx >= N) return;
        if (S[idx] == idx) {
            auto it = wrong.find(idx);
            if (it != wrong.end()) wrong.erase(it);
        } else {
            wrong.insert(idx);
        }
    };
    
    vector<pair<int,int>> ans;
    long long sumDist = 0;
    
    for (int k = 0; k < M; ++k) {
        if (wrong.empty()) break;
        
        int x = Jx[k], y = Jy[k];
        if (x != y) {
            int sx = S[x], sy = S[y];
            swap(S[x], S[y]);
            pos[sx] = y; pos[sy] = x;
            update_wrong(x);
            update_wrong(y);
        }
        
        if (wrong.empty()) {
            // Perform a dummy swap this round and finish
            ans.emplace_back(0, 0);
            // sumDist unchanged
            break;
        }
        
        int i = *wrong.begin();
        int j = pos[i];
        // i must be wrong, so j != i
        ans.emplace_back(i, j);
        sumDist += llabs((long long)i - (long long)j);
        if (i != j) {
            int si = S[i], sj = S[j];
            swap(S[i], S[j]);
            pos[si] = j; pos[sj] = i;
            update_wrong(i);
            update_wrong(j);
        }
        
        if (wrong.empty()) break;
    }
    
    int R = (int)ans.size();
    cout << R << "\n";
    for (auto &p : ans) {
        cout << p.first << " " << p.second << "\n";
    }
    long long V = (long long)R * sumDist;
    cout << V << "\n";
    
    return 0;
}