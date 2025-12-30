#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0): n(n), bit(n+1,0) {}
    void init(int n_) { n = n_; bit.assign(n+1,0); }
    void add(int idx, int delta){
        for(; idx<=n; idx += idx & -idx) bit[idx] += delta;
    }
    int sumPrefix(int idx){
        int s=0;
        for(; idx>0; idx -= idx & -idx) s += bit[idx];
        return s;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }
    // find minimal t such that pos[t] < pos[t+1] < ... < pos[n]
    int i = n-1;
    int prev = pos[n];
    while(i >= 1 && pos[i] < prev){
        prev = pos[i];
        --i;
    }
    int t = i + 1;
    int m = t - 1; // number of moves

    vector<pair<int,int>> moves;
    long long sumY = 0;

    if(m > 0){
        int sizeBIT = n + m + 2;
        Fenwick bit(sizeBIT);
        vector<int> posBIT(n+1, 0);
        // Initialize: place original array at positions m+1 .. m+n
        for(int idx = 1; idx <= n; ++idx){
            int value = v[idx];
            posBIT[value] = m + idx;
            bit.add(posBIT[value], 1);
        }
        int front = m; // next free front position
        for(int val = t-1; val >= 1; --val){
            int idx = posBIT[val];
            int x = bit.sumPrefix(idx);
            int y = 1;
            moves.push_back({x, y});
            sumY += y;
            bit.add(idx, -1);
            posBIT[val] = front;
            bit.add(posBIT[val], 1);
            --front;
        }
    }

    long long finalCost = (sumY + 1) * ( (long long)m + 1 );
    cout << finalCost << " " << moves.size() << "\n";
    for(auto &pr : moves){
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}