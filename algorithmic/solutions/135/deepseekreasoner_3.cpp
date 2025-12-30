#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>
using namespace std;

int n;
bool is_closest(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    int r;
    cin >> r;
    bool found = false;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        if ((u == a && v == b) || (u == b && v == a))
            found = true;
    }
    return found;
}

int main() {
    int k;
    cin >> k >> n;
    
    const int M = 10; // sample size
    vector<int> sample(M);
    for (int i = 0; i < M; ++i) sample[i] = i;
    
    // frequency of closest pairs within sample
    int freq[10][10] = {0};
    
    // query all triples in sample
    for (int a = 0; a < M; ++a)
        for (int b = a+1; b < M; ++b)
            for (int c = b+1; c < M; ++c) {
                cout << "? " << a << " " << b << " " << c << endl;
                cout.flush();
                int r;
                cin >> r;
                for (int i = 0; i < r; ++i) {
                    int u, v;
                    cin >> u >> v;
                    if (u > v) swap(u, v);
                    freq[u][v]++;
                    freq[v][u]++;
                }
            }
    
    // DP for maximum weight Hamiltonian cycle (weight = frequency)
    const int FULL = (1 << M) - 1;
    int dp[1<<M][M], parent[1<<M][M];
    memset(dp, -1, sizeof(dp));
    for (int i = 0; i < M; ++i)
        dp[1<<i][i] = 0;
    
    for (int mask = 1; mask <= FULL; ++mask) {
        for (int i = 0; i < M; ++i) {
            if (dp[mask][i] < 0) continue;
            for (int j = 0; j < M; ++j) {
                if (mask & (1<<j)) continue;
                int new_mask = mask | (1<<j);
                int val = dp[mask][i] + freq[i][j];
                if (val > dp[new_mask][j]) {
                    dp[new_mask][j] = val;
                    parent[new_mask][j] = i;
                }
            }
        }
    }
    
    // find best cycle ending back at start (we fix start = 0)
    int best_end = -1, best_weight = -1;
    for (int j = 1; j < M; ++j) {
        if (dp[FULL][j] < 0) continue;
        int w = dp[FULL][j] + freq[j][0];
        if (w > best_weight) {
            best_weight = w;
            best_end = j;
        }
    }
    
    // reconstruct path from 0 to best_end
    vector<int> path;
    int mask = FULL, cur = best_end;
    while (mask != (1<<0)) {
        path.push_back(cur);
        int prev = parent[mask][cur];
        mask ^= (1<<cur);
        cur = prev;
    }
    path.push_back(0);
    reverse(path.begin(), path.end()); // now path[0]=0, path[M-1]=best_end
    
    // choose p0 as the vertex with highest total frequency
    int best_sum = -1, p0 = -1;
    for (int i = 0; i < M; ++i) {
        int sum = 0;
        for (int j = 0; j < M; ++j) sum += freq[i][j];
        if (sum > best_sum) {
            best_sum = sum;
            p0 = i;
        }
    }
    
    // rotate path so that p0 comes first
    int pos = find(path.begin(), path.end(), p0) - path.begin();
    vector<int> ord(M);
    for (int i = 0; i < M; ++i)
        ord[i] = path[(pos + i) % M];
    
    // insert remaining doors one by one
    for (int x = M; x < n; ++x) {
        int m = ord.size();
        int lo = 1, hi = m-1;
        int ins = m; // default insert at the end
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            // if (p0, ord[mid]) is NOT closest, then x lies between p0 and ord[mid]
            if (!is_closest(p0, ord[mid], x)) {
                ins = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        ord.insert(ord.begin() + ins, x);
    }
    
    // output the final cyclic order
    cout << "!";
    for (int i = 0; i < n; ++i)
        cout << " " << ord[i];
    cout << endl;
    cout.flush();
    
    return 0;
}