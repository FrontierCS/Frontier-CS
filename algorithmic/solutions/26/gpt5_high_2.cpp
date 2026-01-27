#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0) { init(n); }
    void init(int n_) { n = n_; bit.assign(n+1, 0); }
    void add(int idx, int val) { for (; idx <= n; idx += idx & -idx) bit[idx] += val; }
    int sum(int idx) const { int r = 0; for (; idx > 0; idx -= idx & -idx) r += bit[idx]; return r; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n+1);
    for (int i = 1; i <= n; ++i) cin >> v[i];
    
    vector<int> posVal(n+1);
    for (int i = 1; i <= n; ++i) posVal[v[i]] = i;
    
    int t = n;
    for (int i = n-1; i >= 1; --i) {
        if (posVal[i] < posVal[i+1]) t = i;
        else break;
    }
    
    int M = 2*n + 5;
    Fenwick bit(M);
    vector<int> posCoord(n+1);
    for (int i = 1; i <= n; ++i) {
        posCoord[v[i]] = n + i;
        bit.add(posCoord[v[i]], 1);
    }
    int frontPtr = n;
    
    vector<pair<int,int>> moves;
    long long sum_y = 0;
    for (int val = t - 1; val >= 1; --val) {
        int x = bit.sum(posCoord[val]);
        moves.emplace_back(x, 1);
        sum_y += 1;
        bit.add(posCoord[val], -1);
        posCoord[val] = frontPtr;
        bit.add(posCoord[val], 1);
        --frontPtr;
    }
    
    long long k = (long long)moves.size();
    long long min_cost = (sum_y + 1) * (k + 1);
    
    cout << min_cost << " " << moves.size() << "\n";
    for (auto &mv : moves) {
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}