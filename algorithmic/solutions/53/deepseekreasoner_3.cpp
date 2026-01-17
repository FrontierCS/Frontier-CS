#include <bits/stdc++.h>
using namespace std;

int n;

int ask(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    cin >> n;
    int k = n;          // we choose k = n
    cout << k << endl;

    vector<int> p(n + 1, -1);   // p[i] will store the image of i
    vector<vector<int>> D(n + 1, vector<int>(n + 1, 0));

    // Test each unordered pair (a,b) with two queries
    for (int a = 1; a <= n; ++a) {
        for (int b = a + 1; b <= n; ++b) {
            // Query 1: a at position 1, b at position 2, rest increasing
            vector<int> q1(n);
            q1[0] = a;
            q1[1] = b;
            int idx = 2;
            for (int x = 1; x <= n; ++x)
                if (x != a && x != b)
                    q1[idx++] = x;
            int A1 = ask(q1);

            // Query 2: b at position 1, a at position 2, rest increasing
            vector<int> q2(n);
            q2[0] = b;
            q2[1] = a;
            idx = 2;
            for (int x = 1; x <= n; ++x)
                if (x != a && x != b)
                    q2[idx++] = x;
            int A2 = ask(q2);

            int d = A1 - A2;
            D[a][b] = d;
            D[b][a] = -d;

            if (d == 1) {
                p[a] = b;          // p[a] = b and p[b] != a
            } else if (d == -1) {
                p[b] = a;          // p[b] = a and p[a] != b
            }
        }
    }

    // Find elements that are definitely determined
    vector<bool> used(n + 1, false);
    for (int i = 1; i <= n; ++i)
        if (p[i] != -1)
            used[p[i]] = true;

    // Remaining undetermined elements must belong to 2‑cycles.
    // They form pairs (a,b) with p[a]=b and p[b]=a.
    vector<int> unk;
    for (int i = 1; i <= n; ++i)
        if (p[i] == -1)
            unk.push_back(i);

    // Match the remaining elements by brute force:
    // For each a in unk, try every b in unk (b>a) and test if p[a]=b
    // using a single query that exploits the already known edges.
    // We know all edges outside the 2‑cycles, so we can compute the
    // expected answer for a given hypothesis.
    vector<int> known_edges(n + 1, -1);
    for (int i = 1; i <= n; ++i)
        if (p[i] != -1)
            known_edges[i] = p[i];

    // Helper to compute the answer for a given query q and a given
    // permutation perm (represented as an array mapping index -> image).
    auto simulate = [&](const vector<int>& q, const vector<int>& perm) {
        int cnt = 0;
        for (int i = 0; i < n; ++i) {
            if (i + 1 == k) continue;   // i is 0‑based, k is 1‑based
            int val = perm[q[i]];        // p[q[i]]
            // find position of val in q
            int pos = -1;
            for (int j = 0; j < n; ++j)
                if (q[j] == val) {
                    pos = j;
                    break;
                }
            if (pos > i) ++cnt;
        }
        return cnt;
    };

    // Try to match the unknowns
    int m = unk.size();
    vector<bool> paired(m, false);
    for (int i = 0; i < m; ++i) {
        if (paired[i]) continue;
        int a = unk[i];
        for (int j = i + 1; j < m; ++j) {
            if (paired[j]) continue;
            int b = unk[j];

            // Build query: a at 1, b at 2, others in increasing order
            vector<int> q(n);
            q[0] = a;
            q[1] = b;
            idx = 2;
            for (int x = 1; x <= n; ++x)
                if (x != a && x != b)
                    q[idx++] = x;

            // Hypothesise that p[a]=b and p[b]=a (2‑cycle)
            vector<int> hyp = known_edges;
            hyp[a] = b;
            hyp[b] = a;
            int exp_yes = simulate(q, hyp);

            // Hypothesise that p[a] and p[b] are something else (but still
            // consistent with the rest). Since they must map to each other
            // in a 2‑cycle, the only other possibility is that they are not
            // paired together. However, because we are inside the set of
            // unknowns, the only way they are not paired is if each is
            // paired with another element. But then the query answer would
            // differ. We can instead ask the real query and compare to exp_yes.
            int real = ask(q);

            if (real == exp_yes) {
                p[a] = b;
                p[b] = a;
                paired[i] = paired[j] = true;
                break;
            }
        }
    }

    // Output the permutation
    cout << "!";
    for (int i = 1; i <= n; ++i)
        cout << " " << p[i];
    cout << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}