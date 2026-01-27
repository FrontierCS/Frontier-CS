#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Global array to store the result
int a[200005];
int n;

struct QueryResult {
    int x;
    int f;
};

// Function to perform a query
QueryResult query(int l, int r) {
    if (l > r) return {-1, -1};
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x;
    if (x == -1) exit(0); // Invalid query or error
    cin >> f;
    return {x, f};
}

void solve(int l, int r) {
    if (l > r) return;

    // Get the mode of the current range
    QueryResult qr = query(l, r);
    int x = qr.x;
    int f = qr.f;

    // If the frequency equals the range length, fill the array
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) {
            a[i] = x;
        }
        return;
    }

    // Binary search to find the start position S of the block of x
    // The block is [S, S + f - 1]
    int search_l = l;
    int search_r = r - f + 1;
    int S = -1;

    while (search_l <= search_r) {
        int mid = search_l + (search_r - search_l) / 2;
        QueryResult q = query(mid, mid + f - 1);

        if (q.x == x && q.f == f) {
            S = mid;
            break;
        }

        if (q.x < x) {
            // Elements in window are smaller than x, so we are to the left of the x-block
            search_l = mid + 1;
        } else if (q.x > x) {
            // Elements in window are larger than x, so we are to the right of the x-block
            search_r = mid - 1;
        } else {
            // q.x == x but q.f < f
            // We are overlapping the block, but not perfectly aligned.
            // The intersection length is q.f.
            // There are two candidates for S depending on whether we are to the left or right of S.
            int c = q.f;
            int s1 = mid + f - c; // Case: mid < S (overlap is suffix of window)
            int s2 = mid - f + c; // Case: mid > S (overlap is prefix of window)
            
            // We need to check which one is correct. One extra query suffices.
            bool s1_correct = false;
            if (s1 >= l && s1 <= r - f + 1) {
                QueryResult q1 = query(s1, s1 + f - 1);
                if (q1.x == x && q1.f == f) {
                    S = s1;
                    s1_correct = true;
                }
            }
            
            if (!s1_correct) {
                S = s2;
            }
            break;
        }
    }

    // Fill the determined block
    for (int i = 0; i < f; ++i) {
        a[S + i] = x;
    }

    // Recurse on left and right subsegments
    solve(l, S - 1);
    solve(S + f, r);
}

int main() {
    // Interactive problems require flushing output.
    // std::endl performs a flush.
    
    if (cin >> n) {
        solve(1, n);

        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << a[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}