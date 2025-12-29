#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Precompute powers of 3 up to N
    vector<long long> pow3(N + 1, 1);
    for (int i = 1; i <= N; ++i) pow3[i] = pow3[i - 1] * 3LL;

    long long start = 0; // all balls in basket 1 -> digit 0
    long long goal = 0;  // all balls in basket 3 -> digit 2
    for (int i = 0; i < N; ++i) goal += 2LL * pow3[i];

    if (start == goal) {
        cout << 0 << '\n';
        return 0;
    }

    struct PrevInfo {
        long long parent;
        unsigned char fromBasket;
        unsigned char toBasket;
    };

    unordered_map<long long, PrevInfo> prev;
    prev.reserve(1 << 20);
    prev.max_load_factor(0.7f);

    queue<long long> q;
    q.push(start);
    prev[start] = {-1, 0, 0};

    bool found = false;

    while (!q.empty() && !found) {
        long long s = q.front(); q.pop();

        // Decode state s into basket positions
        vector<int> pos(N);
        vector<int> buckets[3];
        long long tmp = s;
        for (int i = 0; i < N; ++i) {
            int d = (int)(tmp % 3LL);
            pos[i] = d;
            buckets[d].push_back(i + 1); // store ball labels (1..N)
            tmp /= 3LL;
        }

        for (int a = 0; a < 3; ++a) {
            if (buckets[a].empty()) continue;

            int k = (int)buckets[a].size();
            int centerIdx = k / 2; // floor(k/2), 0-based
            int centerBallLabel = buckets[a][centerIdx];
            int centerBallIndex = centerBallLabel - 1; // 0-based ball index

            for (int b = 0; b < 3; ++b) {
                if (b == a) continue;

                const auto &dest = buckets[b];
                int t = (int)dest.size();
                int requiredSmaller = (t + 1) / 2; // floor((t+1)/2)

                // count how many in dest are < centerBallLabel
                int sSmall = lower_bound(dest.begin(), dest.end(), centerBallLabel) - dest.begin();
                if (sSmall != requiredSmaller) continue;

                long long newState = s + (long long)(b - a) * pow3[centerBallIndex];
                if (prev.find(newState) == prev.end()) {
                    prev[newState] = {s, (unsigned char)a, (unsigned char)b};
                    if (newState == goal) {
                        found = true;
                        break;
                    }
                    q.push(newState);
                }
            }
            if (found) break;
        }
    }

    if (!found) {
        cout << 0 << '\n';
        return 0;
    }

    // Reconstruct path
    vector<pair<int,int>> moves;
    long long cur = goal;
    while (true) {
        auto it = prev.find(cur);
        if (it == prev.end()) break; // shouldn't happen
        if (it->second.parent == -1) break;
        moves.push_back({it->second.fromBasket + 1, it->second.toBasket + 1});
        cur = it->second.parent;
    }
    reverse(moves.begin(), moves.end());

    cout << moves.size() << '\n';
    for (auto &mv : moves) {
        cout << mv.first << ' ' << mv.second << '\n';
    }
    return 0;
}