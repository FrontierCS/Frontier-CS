#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>
using namespace std;

int N;
int totalQueries = 0;
const int MAXN = 1000; // 2N <= 1000

int query(const vector<int>& included) {
    totalQueries++;
    cout << "Query " << included.size();
    for (int x : included) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Query the set of all chameleons except those in 'excluded'
int query_exclude(const vector<int>& excluded) {
    static bool bad[MAXN+1];
    memset(bad, 0, sizeof(bad));
    for (int x : excluded) bad[x] = true;
    vector<int> included;
    for (int i = 1; i <= 2*N; i++) {
        if (!bad[i]) included.push_back(i);
    }
    return query(included);
}

bool test_pair(int i, int j) {
    int res = query_exclude({i, j});
    return (res == N-1);
}

// Returns true if the partner of 'a' is in set S (S is a vector of candidate IDs)
bool test_subset(int a, const vector<int>& S) {
    vector<int> excl = {a};
    excl.insert(excl.end(), S.begin(), S.end());
    int res = query_exclude(excl);
    return (res == N-1);
}

// Binary search to find the index of the partner of 'a' within the list UB.
// Assumes partner(a) is in UB.
int binary_search_partner(int a, const vector<int>& UB) {
    int lo = 0, hi = (int)UB.size() - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        vector<int> subset(UB.begin() + lo, UB.begin() + mid + 1);
        if (test_subset(a, subset)) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

// Recursive function to find all color pairs within a set V.
// Returns (list of pairs, list of unmatched vertices in V).
pair<vector<pair<int,int>>, vector<int>> process(const vector<int>& V) {
    vector<pair<int,int>> pairs;
    vector<int> unmatched;
    int sz = V.size();
    if (sz == 0) {
        return {pairs, unmatched};
    }
    if (sz == 1) {
        unmatched.push_back(V[0]);
        return {pairs, unmatched};
    }
    if (sz == 2) {
        int a = V[0], b = V[1];
        if (test_pair(a, b)) {
            pairs.push_back({a, b});
        } else {
            unmatched.push_back(a);
            unmatched.push_back(b);
        }
        return {pairs, unmatched};
    }

    // Split into two halves
    int mid = sz / 2;
    vector<int> A(V.begin(), V.begin() + mid);
    vector<int> B(V.begin() + mid, V.end());

    auto [pairsA, unA] = process(A);
    auto [pairsB, unB] = process(B);

    pairs.insert(pairs.end(), pairsA.begin(), pairsA.end());
    pairs.insert(pairs.end(), pairsB.begin(), pairsB.end());

    // Match between unA and unB
    vector<int> UB = unB; // copy for modification
    for (int a : unA) {
        if (UB.empty()) {
            unmatched.push_back(a);
            continue;
        }
        // Check if partner(a) is in UB
        if (test_subset(a, UB)) {
            int idx = binary_search_partner(a, UB);
            int b = UB[idx];
            pairs.push_back({a, b});
            // Remove b from UB
            UB.erase(UB.begin() + idx);
        } else {
            unmatched.push_back(a);
        }
    }
    // Remaining vertices in UB are unmatched (their partners are not in unA)
    for (int b : UB) {
        unmatched.push_back(b);
    }

    return {pairs, unmatched};
}

int main() {
    cin >> N;
    vector<int> all(2*N);
    for (int i = 0; i < 2*N; i++) {
        all[i] = i+1;
    }

    auto [pairs, unmatched] = process(all);
    // unmatched should be empty
    // Output answers
    for (auto& p : pairs) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }

    return 0;
}