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

    auto is_sorted_now = [&]() {
        for (int i = 0; i < N; ++i) if (S[i] != i) return false;
        return true;
    };

    set<int> bad;
    for (int i = 0; i < N; ++i) if (S[i] != i) bad.insert(i);

    auto applySwap = [&](int a, int b) {
        if (a == b) return;
        bad.erase(a);
        bad.erase(b);
        int va = S[a], vb = S[b];
        swap(S[a], S[b]);
        pos[va] = b;
        pos[vb] = a;
        if (S[a] != a) bad.insert(a);
        if (S[b] != b) bad.insert(b);
    };

    vector<pair<int,int>> ourMoves;
    ourMoves.reserve(M);
    long long sumDist = 0;

    if (bad.empty()) {
        cout << 0 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    for (int k = 0; k < M; ++k) {
        // Jerry's move
        applySwap(J[k].first, J[k].second);

        // Our move
        int u = 0, v = 0;
        if (bad.empty()) {
            // Already sorted, perform dummy swap and stop
            ourMoves.emplace_back(0, 0);
            // sumDist += 0;
            break;
        } else {
            int nx = -1, ny = -1;
            if (k < M - 1) {
                nx = J[k+1].first;
                ny = J[k+1].second;
            }
            int iCandidate = -1, jCandidate = -1;

            if (k < M - 1) {
                int tries = 0;
                for (auto it = bad.begin(); it != bad.end() && tries < 50; ++it, ++tries) {
                    int i = *it;
                    int j = pos[i];
                    if (i == j) continue; // shouldn't happen for bad
                    if (i != nx && i != ny && j != nx && j != ny) {
                        iCandidate = i; jCandidate = j;
                        break;
                    }
                }
            }
            if (iCandidate == -1) {
                int i = *bad.begin();
                int j = pos[i];
                iCandidate = i; jCandidate = j;
            }
            u = iCandidate; v = jCandidate;

            applySwap(u, v);
            sumDist += llabs((long long)u - (long long)v);
            ourMoves.emplace_back(u, v);

            if (bad.empty()) break;
        }
    }

    int R = (int)ourMoves.size();
    long long V = (long long)R * sumDist;

    cout << R << "\n";
    for (auto &p : ourMoves) {
        cout << p.first << " " << p.second << "\n";
    }
    cout << V << "\n";

    return 0;
}