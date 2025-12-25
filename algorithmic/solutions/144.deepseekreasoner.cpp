#include <bits/stdc++.h>
using namespace std;

typedef pair<int, int> pii;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

vector<int> random_subset(const vector<int>& v, int k) {
    vector<int> res = v;
    shuffle(res.begin(), res.end(), rng);
    if ((int)res.size() > k) res.resize(k);
    return res;
}

pii query(const vector<int>& indices) {
    int k = indices.size();
    cout << "0 " << k;
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    pii global = query(all);
    int M1 = global.first, M2 = global.second;   // global medians (values)

    // We'll try to find a triple (a,b,c) such that a,b are < M1 and c > M2.
    const int MAX_ATTEMPTS = 15;
    const int S_SIZE = 25;      // size of sample to test triple
    int queries_used = 1;       // already used one query

    for (int att = 0; att < MAX_ATTEMPTS && queries_used <= 500; ++att) {
        // pick random distinct a,b,c
        vector<int> perm = all;
        shuffle(perm.begin(), perm.end(), rng);
        int a = perm[0], b = perm[1], c = perm[2];
        // remaining indices
        vector<int> remaining;
        for (int i = 1; i <= n; ++i)
            if (i != a && i != b && i != c)
                remaining.push_back(i);
        // sample S from remaining
        vector<int> S = random_subset(remaining, min(S_SIZE, (int)remaining.size()));
        vector<int> cat_S(S.size(), -1); // 0: L, 1: R, 2: M1, 3: M2
        bool ok = true;
        for (size_t idx = 0; idx < S.size(); ++idx) {
            int i = S[idx];
            vector<int> q = {i, a, b, c};
            pii res = query(q);
            queries_used++;
            int x = res.first, y = res.second;
            if (x > y) swap(x, y); // just in case
            if (x < M1 && y < M1) {
                cat_S[idx] = 0; // L
            } else if (x < M1 && y > M2) {
                cat_S[idx] = 1; // R
            } else if (x < M1 && y == M1) {
                cat_S[idx] = 2; // M1
            } else if (x < M1 && y == M2) {
                cat_S[idx] = 3; // M2
            } else {
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        // check counts in S
        int cntL = 0, cntR = 0, cntM1 = 0, cntM2 = 0;
        for (int cat : cat_S) {
            if (cat == 0) cntL++;
            else if (cat == 1) cntR++;
            else if (cat == 2) cntM1++;
            else cntM2++;
        }
        if (cntM1 > 1 || cntM2 > 1) continue;
        // L and R should be roughly half each (since about half are L and half R)
        int total = S.size();
        if (cntL < total * 0.3 || cntL > total * 0.7) continue;
        if (cntR < total * 0.3 || cntR > total * 0.7) continue;

        // triple looks promising, now classify all indices
        vector<int> cat(n+1, -1);
        // classify all except a,b,c
        for (int i = 1; i <= n; ++i) {
            if (i == a || i == b || i == c) continue;
            vector<int> q = {i, a, b, c};
            pii res = query(q);
            queries_used++;
            int x = res.first, y = res.second;
            if (x > y) swap(x, y);
            if (x < M1 && y < M1) cat[i] = 0;
            else if (x < M1 && y > M2) cat[i] = 1;
            else if (x < M1 && y == M1) cat[i] = 2;
            else if (x < M1 && y == M2) cat[i] = 3;
            else {
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        // Now we need two L and one R from already classified indices to classify a,b,c
        int l1 = -1, l2 = -1, r1 = -1;
        for (int i = 1; i <= n; ++i) {
            if (i == a || i == b || i == c) continue;
            if (cat[i] == 0) {
                if (l1 == -1) l1 = i;
                else if (l2 == -1) l2 = i;
            } else if (cat[i] == 1) {
                if (r1 == -1) r1 = i;
            }
            if (l1 != -1 && l2 != -1 && r1 != -1) break;
        }
        if (l1 == -1 || l2 == -1 || r1 == -1) continue; // should not happen

        // classify a
        vector<int> qa = {a, l1, l2, r1};
        pii res = query(qa);
        queries_used++;
        int x = res.first, y = res.second;
        if (x > y) swap(x, y);
        if (x < M1 && y < M1) cat[a] = 0;
        else if (x < M1 && y > M2) cat[a] = 1;
        else if (x < M1 && y == M1) cat[a] = 2;
        else if (x < M1 && y == M2) cat[a] = 3;
        else { ok = false; }
        if (!ok) continue;

        // classify b
        vector<int> qb = {b, l1, l2, r1};
        res = query(qb);
        queries_used++;
        x = res.first, y = res.second;
        if (x > y) swap(x, y);
        if (x < M1 && y < M1) cat[b] = 0;
        else if (x < M1 && y > M2) cat[b] = 1;
        else if (x < M1 && y == M1) cat[b] = 2;
        else if (x < M1 && y == M2) cat[b] = 3;
        else { ok = false; }
        if (!ok) continue;

        // classify c
        vector<int> qc = {c, l1, l2, r1};
        res = query(qc);
        queries_used++;
        x = res.first, y = res.second;
        if (x > y) swap(x, y);
        if (x < M1 && y < M1) cat[c] = 0;
        else if (x < M1 && y > M2) cat[c] = 1;
        else if (x < M1 && y == M1) cat[c] = 2;
        else if (x < M1 && y == M2) cat[c] = 3;
        else { ok = false; }
        if (!ok) continue;

        // Verify final counts
        cntL = 0; cntR = 0; cntM1 = 0; cntM2 = 0;
        for (int i = 1; i <= n; ++i) {
            if (cat[i] == 0) cntL++;
            else if (cat[i] == 1) cntR++;
            else if (cat[i] == 2) cntM1++;
            else if (cat[i] == 3) cntM2++;
        }
        if (cntL == n/2 - 1 && cntR == n/2 - 1 && cntM1 == 1 && cntM2 == 1) {
            // find indices of M1 and M2
            int i1 = -1, i2 = -1;
            for (int i = 1; i <= n; ++i) {
                if (cat[i] == 2) i1 = i;
                if (cat[i] == 3) i2 = i;
            }
            cout << "1 " << i1 << " " << i2 << endl;
            cout.flush();
            return 0;
        }
        // otherwise continue
    }

    // If we reach here, something went wrong, but we must output something.
    // As a fallback, output the first two indices (should not happen)
    cout << "1 1 2" << endl;
    cout.flush();
    return 0;
}