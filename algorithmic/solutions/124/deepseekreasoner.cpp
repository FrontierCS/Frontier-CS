#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parity; // 1 for odd, 0 for even
vector<int> val;    // 0 if unknown
int total_sum;

int ask_query(const vector<int>& indices) {
    cout << "? " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

void answer(const vector<int>& perm) {
    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << perm[i];
    cout << endl;
    cout.flush();
    exit(0);
}

int main() {
    cin >> n;
    total_sum = n * (n + 1) / 2;
    parity.resize(n + 1);
    val.resize(n + 1, 0);

    // ---------- Step 1: determine parity ----------
    vector<int> rel_par(n + 1, 0); // relative to index 1
    for (int i = 2; i <= n; i++) {
        vector<int> q = {1, i};
        int ans = ask_query(q);
        rel_par[i] = (ans == 1 ? 0 : 1);
    }
    // count how many have rel_par == 0
    int cnt0 = 1; // index 1 itself
    for (int i = 2; i <= n; i++) if (rel_par[i] == 0) cnt0++;
    int odd1; // parity of index 1: 1 for odd, 0 for even
    if (cnt0 == n / 2) odd1 = 1;
    else odd1 = 0;
    parity[1] = odd1;
    for (int i = 2; i <= n; i++) {
        if (rel_par[i] == 0) parity[i] = odd1;
        else parity[i] = 1 - odd1;
    }

    // ---------- Step 2: find positions of 1 and n ----------
    vector<int> is_cand(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        vector<int> q;
        for (int j = 1; j <= n; j++) if (j != i) q.push_back(j);
        int ans = ask_query(q);
        is_cand[i] = ans;
    }
    vector<int> cands;
    for (int i = 1; i <= n; i++) if (is_cand[i]) cands.push_back(i);
    int A, B; // A -> 1, B -> n
    if (parity[cands[0]] == 1) {
        A = cands[0];
        B = cands[1];
    } else {
        A = cands[1];
        B = cands[0];
    }
    val[A] = 1;
    val[B] = n;

    // ---------- Step 3: initialize unknown sets ----------
    set<int> unknown_idx;
    for (int i = 1; i <= n; i++) if (val[i] == 0) unknown_idx.insert(i);
    set<int> unknown_val;
    for (int v = 2; v <= n - 1; v++) unknown_val.insert(v);

    // known indices separated into low and high (relative to n/2)
    vector<int> low_idx, high_idx;
    if (val[A] <= n / 2) low_idx.push_back(A);
    else high_idx.push_back(A);
    if (val[B] <= n / 2) low_idx.push_back(B);
    else high_idx.push_back(B);

    int sum_known = val[A] + val[B];

    // helper to compute sum of values for a set of indices
    auto sum_of_set = [&](const vector<int>& indices) {
        int s = 0;
        for (int idx : indices) s += val[idx];
        return s;
    };

    // helper to check if a value v is unknown
    auto is_unknown_val = [&](int v) {
        return unknown_val.find(v) != unknown_val.end();
    };

    // try to find a unique v for a given K
    auto try_K = [&](const vector<int>& K) -> int {
        int m = K.size();
        int M = n - m - 1;
        if (M <= 0) return -1;
        int sumK = sum_of_set(K);
        int C = (total_sum - sumK) % M;
        // find all v in unknown_val with v % M == C
        int found = -1;
        int cnt = 0;
        for (int v : unknown_val) {
            if (v % M == C) {
                cnt++;
                found = v;
            }
        }
        if (cnt == 1) return found;
        else return -1;
    };

    // main loop
    while (!unknown_idx.empty()) {
        if (unknown_idx.size() == 1) { // only one left
            int idx = *unknown_idx.begin();
            int v = *unknown_val.begin();
            val[idx] = v;
            break;
        }

        // collect all known indices
        vector<int> all_known;
        for (int i = 1; i <= n; i++) if (val[i] != 0) all_known.push_back(i);

        // try different K candidates
        vector<int> candidate_v;
        vector<int> candidate_K;

        // helper to add if unique v found
        auto add_if_unique = [&](const vector<int>& K) {
            int v = try_K(K);
            if (v != -1) {
                candidate_v.push_back(v);
                candidate_K = K;
                return true;
            }
            return false;
        };

        bool found = false;
        // 1. K = high indices
        if (!high_idx.empty() && add_if_unique(high_idx)) found = true;
        // 2. K = low indices
        if (!found && !low_idx.empty() && add_if_unique(low_idx)) found = true;
        // 3. K = high without max (by value)
        if (!found && high_idx.size() >= 2) {
            // find index with max value in high_idx
            int max_val = -1, max_idx = -1;
            for (int idx : high_idx) {
                if (val[idx] > max_val) {
                    max_val = val[idx];
                    max_idx = idx;
                }
            }
            vector<int> K = high_idx;
            K.erase(remove(K.begin(), K.end(), max_idx), K.end());
            if (add_if_unique(K)) found = true;
        }
        // 4. K = low without min (by value)
        if (!found && low_idx.size() >= 2) {
            int min_val = n + 1, min_idx = -1;
            for (int idx : low_idx) {
                if (val[idx] < min_val) {
                    min_val = val[idx];
                    min_idx = idx;
                }
            }
            vector<int> K = low_idx;
            K.erase(remove(K.begin(), K.end(),