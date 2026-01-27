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
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        J[i] = {x, y};
    }

    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;

    auto is_sorted_now = [&]() -> bool {
        // Quick check using a maintained counter is better; but fallback check
        // This function may be called only if needed; we will maintain badCount anyway.
        for (int i = 0; i < N; ++i) if (S[i] != i) return false;
        return true;
    };

    int badCount = 0;
    for (int i = 0; i < N; ++i) if (S[i] != i) ++badCount;

    vector<int> cands;
    cands.reserve(N + 4LL*M);
    for (int i = 0; i < N; ++i) if (S[i] != i) cands.push_back(i);

    auto applySwap = [&](int a, int b) {
        if (a == b) return;
        int beforeBad = (S[a] != a) + (S[b] != b);
        int va = S[a], vb = S[b];
        swap(S[a], S[b]);
        pos[va] = b;
        pos[vb] = a;
        int afterBad = (S[a] != a) + (S[b] != b);
        badCount += (afterBad - beforeBad);
    };

    vector<pair<int,int>> myMoves;
    myMoves.reserve(M);
    long long sumDist = 0;
    int scanPtr = 0;

    for (int k = 0; k < M; ++k) {
        if (badCount == 0) break;

        // Jerry's move
        int x = J[k].first, y = J[k].second;
        applySwap(x, y);
        if (x != y) { cands.push_back(x); cands.push_back(y); }

        // Our move
        if (badCount == 0) {
            // Already sorted; do a dummy swap
            myMoves.emplace_back(0, 0);
            continue;
        }

        int i = -1;
        while (!cands.empty()) {
            int t = cands.back(); cands.pop_back();
            if (S[t] != t) { i = t; break; }
        }
        if (i == -1) {
            // Fallback scan (should rarely happen)
            for (int t = 0; t < N; ++t) {
                int idx = scanPtr;
                if (++scanPtr == N) scanPtr = 0;
                if (S[idx] != idx) { i = idx; break; }
            }
        }
        if (i == -1) {
            // Should not happen; perform dummy swap
            myMoves.emplace_back(0, 0);
            continue;
        }
        int j = pos[i];
        applySwap(i, j);
        myMoves.emplace_back(i, j);
        sumDist += llabs((long long)i - (long long)j);
        if (i != j) { cands.push_back(i); cands.push_back(j); }
    }

    int R = (int)myMoves.size();
    cout << R << '\n';
    for (auto &p : myMoves) {
        cout << p.first << ' ' << p.second << '\n';
    }
    long long V = (long long)R * sumDist;
    cout << V << '\n';

    return 0;
}