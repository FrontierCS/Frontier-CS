#include <cstdio>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cstdlib>
#include <ctime>

using namespace std;

const int MAXN = 43000;
const int MAXS = 2*MAXN + 5;

int cur_distinct;
bool paired[MAXS];

int query(int x) {
    printf("? %d\n", x);
    fflush(stdout);
    int r;
    scanf("%d", &r);
    cur_distinct = r;
    return r;
}

void answer(int a, int b) {
    printf("! %d %d\n", a, b);
    fflush(stdout);
    paired[a] = paired[b] = true;
}

// Precondition: device contains exactly the slices in L (all of them).
// r is not in device.
// Returns the slice in L that is the partner of r.
int find_partner(int r, vector<int>& L) {
    int k = L.size();
    vector<bool> in_dev(k, true);
    int lo = 0, hi = k;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        // make sure L[lo..mid) are out, L[mid..hi) are in
        for (int i = lo; i < mid; ++i) {
            if (in_dev[i]) {
                query(L[i]);
                in_dev[i] = false;
            }
        }
        for (int i = mid; i < hi; ++i) {
            if (!in_dev[i]) {
                query(L[i]);
                in_dev[i] = true;
            }
        }
        // now device contains exactly L[mid..hi)
        int before = cur_distinct;
        int after = query(r); // insert r
        if (after > before) {
            // partner is in [lo, mid)
            query(r); // remove r
            // remove L[mid..hi) from device
            for (int i = mid; i < hi; ++i) {
                if (in_dev[i]) {
                    query(L[i]);
                    in_dev[i] = false;
                }
            }
            hi = mid;
        } else {
            // partner is in [mid, hi)
            query(r); // remove r
            // device still contains L[mid..hi)
            lo = mid;
            // L[lo..mid) are already out, in_dev correctly false
        }
    }
    int partner = L[lo];
    // clean up: remove any remaining L slices from device
    for (int i = 0; i < k; ++i) {
        if (in_dev[i]) {
            query(L[i]);
        }
    }
    // now device is empty
    return partner;
}

// Precondition: device contains all slices in L and all slices in R.
// Every slice in R has its partner in L.
// After the call, device is empty.
void match_general(vector<int> L, vector<int> R) {
    if (R.empty()) {
        for (int x : L) query(x);
        return;
    }
    if (R.size() == 1) {
        int r = R[0];
        query(r); // remove r, now device contains L
        int partner = find_partner(r, L);
        answer(r, partner);
        // find_partner already left device empty
        return;
    }
    // recursive case
    int split = L.size() / 2;
    vector<int> L1(L.begin(), L.begin() + split);
    vector<int> L2(L.begin() + split, L.end());
    // remove L2 from device
    for (int x : L2) query(x);
    // now device contains L1 and R
    vector<int> R1, R2;
    int cur = cur_distinct;
    for (int r : R) {
        int new_r = query(r); // remove r
        if (new_r < cur) {
            R2.push_back(r);
        } else {
            R1.push_back(r);
        }
        cur = new_r;
    }
    // now device contains only L1 (all R removed)
    // insert R1
    for (int r : R1) query(r);
    match_general(L1, R1);
    // device empty now
    // insert L2 and R2
    for (int x : L2) query(x);
    for (int r : R2) query(r);
    match_general(L2, R2);
    // device empty
}

// Precondition: device is empty.
// After the call, device is empty.
void solve(vector<int> slices) {
    if (slices.size() == 2) {
        answer(slices[0], slices[1]);
        return;
    }
    int m = slices.size();
    int half = m / 2;