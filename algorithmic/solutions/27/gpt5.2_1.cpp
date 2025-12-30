#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXS = 320;

static vector<int> findCliqueGreedy(int s, int need,
                                   const vector<bitset<MAXS>>& used,
                                   const bitset<MAXS>& allMask,
                                   mt19937& rng) {
    if (need <= 1) return {};

    vector<int> verts(s);
    iota(verts.begin(), verts.end(), 0);

    // Rank starts by current available degree (descending), with a tiny shuffle for ties.
    vector<int> starts = verts;
    shuffle(starts.begin(), starts.end(), rng);
    stable_sort(starts.begin(), starts.end(), [&](int a, int b) {
        size_t da = (allMask & (~used[a])).count();
        size_t db = (allMask & (~used[b])).count();
        return da > db;
    });

    int maxStarts = min(s, 32);
    for (int si = 0; si < maxStarts; si++) {
        int start = starts[si];
        if ((allMask & (~used[start])).count() < (size_t)(need - 1)) continue;

        vector<int> cur;
        cur.reserve(need);
        cur.push_back(start);

        bitset<MAXS> cand = allMask & (~used[start]);

        while ((int)cur.size() < need) {
            if (!cand.any()) break;

            int best = -1;
            size_t bestCnt = 0;

            // Choose next vertex that maximizes remaining candidates after adding it.
            for (int v = 0; v < s; v++) {
                if (!cand.test(v)) continue;
                bitset<MAXS> nc = (cand & (~used[v])) & allMask;
                size_t cnt = nc.count();
                if (cnt > bestCnt || best == -1) {
                    best = v;
                    bestCnt = cnt;
                }
            }

            if (best == -1) break;
            cur.push_back(best);
            cand = (cand & (~used[best])) & allMask;
        }

        if ((int)cur.size() == need) return cur;
    }

    return {};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // Special easy cases
    if (n == 1 || m == 1) {
        int k = n * m;
        cout << k << "\n";
        for (int r = 1; r <= n; r++) {
            for (int c = 1; c <= m; c++) {
                cout << r << " " << c << "\n";
            }
        }
        return 0;
    }
    if (n == 2) {
        int k = m + 1;
        cout << k << "\n";
        for (int c = 1; c <= m; c++) cout << 1 << " " << c << "\n";
        cout << 2 << " " << 1 << "\n";
        return 0;
    }
    if (m == 2) {
        int k = n + 1;
        cout << k << "\n";
        for (int r = 1; r <= n; r++) cout << r << " " << 1 << "\n";
        cout << 1 << " " << 2 << "\n";
        return 0;
    }

    bool swapped = false;
    int origN = n, origM = m;
    if (n > m) {
        swapped = true;
        swap(n, m);
    }
    // Now n <= m. Let items = rows (size n), groups = columns (size m).
    int s = n;      // <= 316 due to n*m <= 1e5
    int L = m;

    mt19937 rng(712367);

    vector<bitset<MAXS>> used(s);
    bitset<MAXS> allMask;
    allMask.reset();
    for (int i = 0; i < s; i++) allMask.set(i);

    for (int i = 0; i < s; i++) {
        used[i].reset();
        used[i].set(i); // prevent selecting same vertex twice in a clique
    }

    long long B = 1LL * s * (s - 1) / 2;
    long long rem = (B * 85) / 100; // use only 85% of pair budget for easier construction

    vector<int> desired(L, 1);
    for (int t = 1; t < s; t++) {
        if (rem < t) break;
        bool any = false;
        for (int i = 0; i < L; i++) {
            if (desired[i] == t && rem >= t) {
                desired[i]++;
                rem -= t;
                any = true;
            }
        }
        if (!any) break;
    }

    vector<int> order(L);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return desired[a] > desired[b];
    });

    vector<vector<int>> neigh(L);

    for (int gid : order) {
        int want = desired[gid];
        if (want <= 1) {
            neigh[gid] = { gid % s };
            continue;
        }

        vector<int> chosen;
        int curWant = want;
        while (curWant >= 2) {
            chosen = findCliqueGreedy(s, curWant, used, allMask, rng);
            if (!chosen.empty()) break;
            curWant--;
        }

        if (chosen.empty()) {
            neigh[gid] = { gid % s };
            continue;
        }

        // Mark used pairs
        for (int i = 0; i < (int)chosen.size(); i++) {
            for (int j = i + 1; j < (int)chosen.size(); j++) {
                int u = chosen[i], v = chosen[j];
                used[u].set(v);
                used[v].set(u);
            }
        }
        neigh[gid] = std::move(chosen);
    }

    vector<pair<int,int>> ans;
    ans.reserve((size_t)origN * (size_t)origM);

    for (int col = 0; col < L; col++) {
        for (int v : neigh[col]) {
            if (!swapped) {
                // (row, col)
                ans.emplace_back(v + 1, col + 1);
            } else {
                // swapped back: groups are rows, items are cols
                ans.emplace_back(col + 1, v + 1);
            }
        }
    }

    cout << ans.size() << "\n";
    for (auto &p : ans) cout << p.first << " " << p.second << "\n";
    return 0;
}