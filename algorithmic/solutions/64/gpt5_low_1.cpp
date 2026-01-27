#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long sum;
    int prev;   // index in previous level
    unsigned char take; // 0 or 1
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    long long sumAll = 0;
    for (auto v : a) sumAll += v;
    
    const int Lmax = 30000;

    vector<vector<Node>> levels;
    levels.reserve(n + 1);
    levels.push_back(vector<Node>(1, Node{0, -1, 0}));

    auto absdiff = [](long long x, long long y)->unsigned long long {
        return (x >= y) ? (unsigned long long)(x - y) : (unsigned long long)(y - x);
    };

    for (int i = 0; i < n; ++i) {
        const auto &prevList = levels.back();
        int P = (int)prevList.size();

        vector<Node> all;
        all.reserve(P * 2);
        for (int j = 0; j < P; ++j) {
            // not take
            all.push_back(Node{prevList[j].sum, j, 0});
            // take
            long long s2 = prevList[j].sum + a[i];
            all.push_back(Node{s2, j, 1});
        }

        sort(all.begin(), all.end(), [](const Node& x, const Node& y){
            if (x.sum != y.sum) return x.sum < y.sum;
            return x.take < y.take; // arbitrary tie-breaker
        });

        long long gap = max(1LL, sumAll / (long long)Lmax);

        vector<Node> next;
        next.reserve(min((int)all.size(), Lmax));
        for (const auto &nd : all) {
            if (next.empty()) {
                next.push_back(nd);
            } else {
                Node &last = next.back();
                if (nd.sum >= last.sum + gap) {
                    next.push_back(nd);
                } else {
                    // If closer to target, replace last kept to keep better quality
                    if (absdiff(nd.sum, T) < absdiff(last.sum, T)) {
                        last = nd;
                    }
                }
            }
        }

        if ((int)next.size() > Lmax) {
            // keep Lmax closest to T, then sort by sum for next iteration
            nth_element(next.begin(), next.begin() + Lmax, next.end(), [&](const Node& x, const Node& y){
                return absdiff(x.sum, T) < absdiff(y.sum, T);
            });
            next.resize(Lmax);
            sort(next.begin(), next.end(), [](const Node& x, const Node& y){
                if (x.sum != y.sum) return x.sum < y.sum;
                return x.take < y.take;
            });
            // Optionally reapply coarse pruning to maintain spacing
            vector<Node> pruned;
            pruned.reserve(next.size());
            for (const auto &nd : next) {
                if (pruned.empty()) pruned.push_back(nd);
                else {
                    Node &last = pruned.back();
                    if (nd.sum >= last.sum + gap) pruned.push_back(nd);
                    else if (absdiff(nd.sum, T) < absdiff(last.sum, T)) last = nd;
                }
            }
            next.swap(pruned);
        }

        levels.push_back(move(next));
    }

    // Find best at final level
    const auto &finalList = levels.back();
    int bestIdx = 0;
    unsigned long long bestErr = ULLONG_MAX;
    for (int i = 0; i < (int)finalList.size(); ++i) {
        auto e = absdiff(finalList[i].sum, T);
        if (e < bestErr) {
            bestErr = e;
            bestIdx = i;
        }
    }

    // Reconstruct solution
    string ans(n, '0');
    int idx = bestIdx;
    for (int i = n - 1; i >= 0; --i) {
        const Node &nd = levels[i + 1][idx];
        if (nd.take) ans[i] = '1';
        idx = nd.prev;
    }

    cout << ans << "\n";
    return 0;
}