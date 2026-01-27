#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }
    
    int S = (N > 1) ? (int)sqrt((double)(N - 1)) : 1;
    if (S < 1) S = 1;
    if (S > N - 1) S = N - 1;
    
    vector<vector<int>> stripes(S);
    if (N > 1) {
        for (int i = 1; i <= N - 1; ++i) {
            int stripe = (int)((1LL * (i - 1) * S) / (N - 1));
            if (stripe >= S) stripe = S - 1;
            stripes[stripe].push_back(i);
        }
        for (int s = 0; s < S; ++s) {
            if (s % 2 == 0) {
                sort(stripes[s].begin(), stripes[s].end(), [&](int a, int b) {
                    if (y[a] != y[b]) return y[a] < y[b];
                    return a < b;
                });
            } else {
                sort(stripes[s].begin(), stripes[s].end(), [&](int a, int b) {
                    if (y[a] != y[b]) return y[a] > y[b];
                    return a < b;
                });
            }
        }
    }
    
    vector<int> path;
    path.reserve(N + 1);
    path.push_back(0);
    for (int s = 0; s < S; ++s) {
        for (int id : stripes[s]) path.push_back(id);
    }
    // If N==1+1=2, stripes may be 1 and contain city 1; else if S could be 0 (when N==1), but N>=2 per constraints.
    // Ensure all cities included (if S==0, fallback to simple order)
    if ((int)path.size() < N) {
        for (int i = 1; i <= N - 1; ++i) path.push_back(i);
    }
    path.push_back(0);
    
    cout << path.size() << '\n';
    for (int v : path) cout << v << '\n';
    return 0;
}