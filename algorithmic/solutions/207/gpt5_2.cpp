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
    vector<pair<int,int>> J(M);
    for (int i = 0; i < M; ++i) cin >> J[i].first >> J[i].second;
    
    // Position of each value
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;
    
    // Count initially correct positions
    int correctCount = 0;
    for (int i = 0; i < N; ++i) if (S[i] == i) ++correctCount;
    
    // If already sorted, output R=0 and V=0
    if (correctCount == N) {
        cout << 0 << "\n";
        cout << 0 << "\n";
        return 0;
    }
    
    // Last touch index for each position by Jerry
    vector<int> last_touch(N, -1);
    for (int k = 0; k < M; ++k) {
        int x = J[k].first, y = J[k].second;
        last_touch[x] = k;
        last_touch[y] = k;
    }
    
    // Buckets: positions that become "available" after round t (t = last_touch + 1), t in [0..M]
    vector<vector<int>> bucket(M + 1);
    for (int i = 0; i < N; ++i) {
        int idx = last_touch[i] + 1; // -1 -> 0; last k -> k+1
        bucket[idx].push_back(i);
    }
    
    deque<int> q;
    // Add positions never touched by Jerry (available from start)
    for (int x : bucket[0]) q.push_back(x);
    
    auto swap_positions = [&](int a, int b) {
        if (a == b) return;
        int va = S[a], vb = S[b];
        if (S[a] == a) --correctCount;
        if (S[b] == b) --correctCount;
        swap(S[a], S[b]);
        pos[va] = b;
        pos[vb] = a;
        if (S[a] == a) ++correctCount;
        if (S[b] == b) ++correctCount;
    };
    
    vector<pair<int,int>> ans;
    ans.reserve(M);
    long long sumDist = 0;
    int R = M;
    
    for (int k = 0; k < M; ++k) {
        // Jerry's move
        int x = J[k].first, y = J[k].second;
        swap_positions(x, y);
        
        // New positions become available after Jerry's move at this round
        if (k + 1 <= M) {
            for (int idx : bucket[k + 1]) q.push_back(idx);
        }
        
        // Our move: try to fix an available wrong position
        int u = 0, v = 0;
        bool did = false;
        while (!q.empty()) {
            int i = q.front();
            q.pop_front();
            if (S[i] == i) continue; // already correct
            int j = S[i];
            // If both i and j are available now and form a 2-cycle, fix both
            if (j != i && last_touch[j] <= k && S[j] == i) {
                u = i; v = j; did = true;
                break;
            } else {
                // Otherwise, put value i to its correct position i
                u = i; v = pos[i]; did = true;
                break;
            }
        }
        if (!did) {
            // no-op
            u = v = 0;
        }
        
        // Apply our move
        swap_positions(u, v);
        sumDist += llabs((long long)u - (long long)v);
        ans.emplace_back(u, v);
        
        // Check if sorted; if yes, stop here
        if (correctCount == N) {
            R = k + 1;
            break;
        }
    }
    
    // If not sorted after all rounds, we still must output something; per problem guarantee, this should not happen.
    // But if it does, we have performed M rounds already.
    if (R == M && correctCount != N) {
        // Nothing more can be done; output as is (assuming inputs respect guarantee)
    }
    
    // Compute V = R * (sum of distances)
    __int128 VV = ( (__int128)R ) * ( (__int128)sumDist );
    unsigned long long V = (unsigned long long)VV;
    
    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << ans[i].first << " " << ans[i].second << "\n";
    }
    cout << V << "\n";
    return 0;
}