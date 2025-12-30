#include <iostream>

using namespace std;

// Function to query the interactor.
// Returns the position of the second largest number in the range [l, r].
int query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;

    // Step 1: Find the position of the second largest element in the entire array [1, n].
    // Let the position of the maximum element be M.
    // Let the position of the second largest element be idx.
    // The query ? 1 n returns idx.
    int idx = query(1, n);

    // Step 2: Determine if M is to the left or to the right of idx.
    bool search_left = false;

    if (idx == n) {
        // If the second largest is at n, the largest must be in [1, n-1].
        search_left = true;
    } else if (idx == 1) {
        // If the second largest is at 1, the largest must be in [2, n].
        search_left = false;
    } else {
        // Query the range [1, idx].
        // If the result is idx, it means the second largest in [1, idx] is A[idx].
        // Since A[idx] is the global second largest, this implies the global largest A[M] is also in [1, idx].
        // Therefore M < idx.
        // If the result is not idx, then M cannot be in [1, idx] (otherwise result would be idx).
        // Therefore M > idx.
        int check = query(1, idx);
        if (check == idx) {
            search_left = true;
        } else {
            search_left = false;
        }
    }

    // Step 3: Binary search for M using idx as an anchor.
    if (search_left) {
        // M is in [1, idx-1].
        // Property: For any range [k, idx] where k <= M, the maximum is A[M] and second max is A[idx].
        // Thus query(k, idx) returns idx.
        // If k > M, the range [k, idx] does not contain M. The max is A[idx], second max is something else.
        // Thus query(k, idx) != idx.
        // We want to find the largest k in [1, idx-1] such that query(k, idx) == idx.
        
        int l = 1, r = idx - 1;
        while (l < r) {
            int mid = (l + r + 1) / 2; // Ceiling division
            if (query(mid, idx) == idx) {
                l = mid; // mid is possible, try larger
            } else {
                r = mid - 1; // mid is too large
            }
        }
        cout << "! " << l << endl;
    } else {
        // M is in [idx+1, n].
        // Property: For any range [idx, k] where k >= M, the maximum is A[M] and second max is A[idx].
        // Thus query(idx, k) returns idx.
        // If k < M, the range [idx, k] does not contain M. The max is A[idx], second max is something else.
        // Thus query(idx, k) != idx.
        // We want to find the smallest k in [idx+1, n] such that query(idx, k) == idx.
        
        int l = idx + 1, r = n;
        while (l < r) {
            int mid = (l + r) / 2; // Floor division
            if (query(idx, mid) == idx) {
                r = mid; // mid is possible, try smaller
            } else {
                l = mid + 1; // mid is too small
            }
        }
        cout << "! " << l << endl;
    }
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}