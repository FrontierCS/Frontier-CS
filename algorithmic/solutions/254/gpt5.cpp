#include <bits/stdc++.h>
using namespace std;

static inline void print_query(const vector<int>& v) {
    cout << "?";
    for (int x : v) cout << " " << x;
    cout << endl;
    cout.flush();
}
static inline int get_answer() {
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}
static inline void print_answer(const vector<int>& v) {
    cout << "!";
    for (int x : v) cout << " " << x;
    cout << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        int N = n * n;
        int k = n - 1; // size of bottom set B
        vector<int> B;
        B.reserve(k);
        vector<char> inB(N + 1, 0);
        for (int i = 1; i <= k; ++i) {
            B.push_back(i);
            inB[i] = 1;
        }
        auto ask = [&](const vector<int>& v)->int {
            print_query(v);
            return get_answer();
        };
        // Stabilize B until a full pass yields no changes
        while (true) {
            bool changed = false;
            for (int x = 1; x <= N; ++x) {
                if (inB[x]) continue;
                vector<int> q = B;
                q.push_back(x);
                int w = ask(q);
                if (w != x) {
                    // replace w in B with x
                    for (int i = 0; i < (int)B.size(); ++i) {
                        if (B[i] == w) {
                            inB[w] = 0;
                            B[i] = x;
                            inB[x] = 1;
                            break;
                        }
                    }
                    changed = true;
                }
            }
            if (!changed) break;
        }
        // After stabilization, for every t not in B, we have explicit t > y for all y in B (since last pass had no changes)

        // Partition into n groups of size n each
        vector<vector<int>> groups(n);
        for (int g = 0; g < n; ++g) {
            groups[g].reserve(n);
            for (int j = 1; j <= n; ++j) {
                int id = g * n + j;
                groups[g].push_back(id);
            }
        }
        // For each group, compute the descending order of its elements that are not in B (the T set)
        vector<vector<int>> sortedT(n);
        // For fast membership checking of B when filling queries
        vector<char> isInB(N + 1, 0);
        for (int x : B) isInB[x] = 1;

        // Utility: fill vector 'q' with B elements not in 'used' until size reaches n
        auto fill_with_B = [&](vector<int>& q, const unordered_set<int>& used) {
            for (int b : B) {
                if ((int)q.size() >= n) break;
                if (!used.count(b)) q.push_back(b);
            }
        };

        for (int g = 0; g < n; ++g) {
            vector<int> groupT;
            for (int x : groups[g]) if (!inB[x]) groupT.push_back(x);
            // Extract in descending order
            // Maintain a set of remaining T elements in this group
            unordered_set<int> rem(groupT.begin(), groupT.end());
            while (!rem.empty()) {
                vector<int> q;
                q.reserve(n);
                unordered_set<int> used;
                for (int x : rem) {
                    q.push_back(x);
                    used.insert(x);
                }
                fill_with_B(q, used);
                int w = ask(q);
                // w must be in rem (since all B are slower than any t not in B)
                // but to be safe if interactor is adversarial, ensure it's in rem
                if (!rem.count(w)) {
                    // In case of unexpected behavior, try to enforce by re-asking with same q until w in rem
                    // However, per problem guarantees, this should not happen after stabilization.
                    // We'll fallback to selecting any rem element to avoid crashes.
                    w = *rem.begin();
                }
                sortedT[g].push_back(w);
                rem.erase(w);
            }
        }

        // Merge across groups to generate global descending list of all elements not in B
        vector<int> idx(n, 0);
        vector<int> result;
        result.reserve(N - (n - 1));

        while ((int)result.size() < N - (n - 1)) {
            vector<int> q;
            q.reserve(n);
            unordered_set<int> used;
            for (int g = 0; g < n; ++g) {
                if (idx[g] < (int)sortedT[g].size()) {
                    int head = sortedT[g][idx[g]];
                    q.push_back(head);
                    used.insert(head);
                } else {
                    // group exhausted: fill with B
                    // later we'll fill all missing with unique B elements
                }
            }
            // Fill remaining slots with B elements distinct from current heads
            for (int b : B) {
                if ((int)q.size() >= n) break;
                if (!used.count(b)) {
                    q.push_back(b);
                    used.insert(b);
                }
            }
            // Invariant: q size should be exactly n
            if ((int)q.size() != n) {
                // As a safeguard, if we still don't have enough due to unexpected issues,
                // fill with any remaining IDs from 1..N not in 'used' (they will be in B or already consumed heads)
                for (int id = 1; id <= N && (int)q.size() < n; ++id) {
                    if (!used.count(id)) {
                        q.push_back(id);
                        used.insert(id);
                    }
                }
            }
            int w = ask(q);
            // w must be among current heads (not in B), since B are slower
            bool found = false;
            for (int g = 0; g < n; ++g) {
                if (idx[g] < (int)sortedT[g].size() && sortedT[g][idx[g]] == w) {
                    result.push_back(w);
                    idx[g]++;
                    found = true;
                    break;
                }
            }
            if (!found) {
                // If winner not found among current heads (unexpected), pick the maximum among heads deterministically
                // Fallback: choose the first available head
                for (int g = 0; g < n; ++g) {
                    if (idx[g] < (int)sortedT[g].size()) {
                        result.push_back(sortedT[g][idx[g]]);
                        idx[g]++;
                        break;
                    }
                }
            }
        }

        print_answer(result);
    }
    return 0;
}