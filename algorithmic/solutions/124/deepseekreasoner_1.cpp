#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

int ask_query(const vector<int>& indices) {
    cout << "? " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int r;
    cin >> r;
    return r;
}

int main() {
    int n;
    cin >> n;

    // ---------- Step 1: Determine parity groups ----------
    vector<int> A, B;
    A.push_back(1);
    for (int i = 2; i <= n; ++i) {
        int r = ask_query({1, i});
        if (r == 1) A.push_back(i);
        else B.push_back(i);
    }
    // A: indices with same parity as p1 (including 1)
    // B: the other indices

    // ---------- Step 2: Find positions of 1 and n ----------
    // Build list of all indices
    vector<int> all_indices(n);
    for (int i = 0; i < n; ++i) all_indices[i] = i + 1;

    int a = -1, b = -1;
    // Find candidate in A
    for (int i : A) {
        vector<int> q;
        for (int j : all_indices) if (j != i) q.push_back(j);
        int r = ask_query(q);
        if (r == 1) a = i;
    }
    // Find candidate in B
    for (int i : B) {
        vector<int> q;
        for (int j : all_indices) if (j != i) q.push_back(j);
        int r = ask_query(q);
        if (r == 1) b = i;
    }

    // ---------- Initialization ----------
    vector<int> val(n + 1, 0);
    vector<bool> known(n + 1, false);
    vector<bool> value_used(n + 1, false);

    val[a] = 1;
    val[b] = n;
    known[a] = known[b] = true;
    value_used[1] = value_used[n] = true;
    int known_count = 2;

    // Candidate sets: cand[i][v] = whether value v is still possible for position i
    vector<vector<bool>> cand(n + 1, vector<bool>(n + 1, false));
    // For positions in A (except a) candidates are odd numbers 3,5,...,n-1
    for (int i : A) {
        if (i != a) {
            for (int v = 3; v <= n - 1; v += 2)
                cand[i][v] = true;
        }
    }
    // For positions in B (except b) candidates are even numbers 2,4,...,n-2
    for (int i : B) {
        if (i != b) {
            for (int v = 2; v <= n - 2; v += 2)
                cand[i][v] = true;
        }
    }

    // Count of remaining candidates for each position
    vector<int> cnt(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (!known[i]) {
            for (int v = 1; v <= n; ++v)
                if (cand[i][v]) ++cnt[i];
        }
    }

    queue<int> single_q;
    for (int i = 1; i <= n; ++i)
        if (!known[i] && cnt[i] == 1)
            single_q.push(i);

    // ---------- Main loop ----------
    while (known_count < n) {
        if (!single_q.empty()) {
            int i = single_q.front(); single_q.pop();
            if (known[i]) continue;

            // Find the only candidate for i
            int the_val = 0;
            for (int v = 1; v <= n; ++v)
                if (cand[i][v]) { the_val = v; break; }

            // Assign value the_val to i
            val[i] = the_val;
            known[i] = true;
            known_count++;
            value_used[the_val] = true;

            // Remove the_val from candidates of other unknown positions
            for (int j = 1; j <= n; ++j) {
                if (!known[j] && cand[j][the_val]) {
                    cand[j][the_val] = false;
                    cnt[j]--;
                    if (cnt[j] == 1) single_q.push(j);
                }
            }
        } else {
            // Pick an unknown position with the smallest number of candidates
            int i_best = -1, min_cand = n + 1;
            for (int i = 1; i <= n; ++i) {
                if (!known[i] && cnt[i] < min_cand) {
                    min_cand = cnt[i];
                    i_best = i;
                }
            }
            int i = i_best;

            // Build set K of known indices
            vector<int> K;
            for (int j = 1; j <= n; ++j)
                if (known[j]) K.push_back(j);
            int m = K.size(); // |K|

            // Query K ∪ {i}
            vector<int> qset = K;
            qset.push_back(i);
            int r = ask_query(qset);

            // Compute sum of known values
            int sum_K = 0;
            for (int j : K) sum_K += val[j];
            int modulus = m + 1;
            int target = (modulus - (sum_K % modulus)) % modulus; // -sum_K mod modulus

            // Update candidates for i according to the response
            if (r == 1) {
                for (int v = 1; v <= n; ++v) {
                    if (cand[i][v] && (v % modulus != target)) {
                        cand[i][v] = false;
                        cnt[i]--;
                    }
                }
            } else {
                for (int v = 1; v <= n; ++v) {
                    if (cand[i][v] && (v % modulus == target)) {
                        cand[i][v] = false;
                        cnt[i]--;
                    }
                }
            }
            if (cnt[i] == 1) single_q.push(i);
        }
    }

    // ---------- Final adjustment ----------
    if (val[1] > n / 2) {
        for (int i = 1; i <= n; ++i)
            val[i] = n + 1 - val[i];
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << val[i];
    cout << endl;
    cout.flush();

    return 0;
}