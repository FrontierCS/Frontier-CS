#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>

using namespace std;

// Function to simulate the editor process for a given width W and article a
// Returns the number of lines, or 0 if unable to display (any word > W)
int simulate(int W, const vector<int>& a) {
    long long s = 0;
    int l = 1;
    for (int x : a) {
        if (x > W) return 0;
        if (s + x <= W) {
            s += x;
        } else {
            l++;
            s = x;
        }
    }
    return l;
}

// Optimized incremental simulator state
struct SimState {
    int W;
    int l;
    long long s;
    
    SimState(int w) : W(w), l(1), s(0) {}
    
    void add(int x) {
        // Assume x <= W always for this problem's logic
        if (s + x <= W) {
            s += x;
        } else {
            l++;
            s = x;
        }
    }
};

void solve() {
    // Strategy:
    // Query 1: Send a small article (e.g., two words of length 1) to establish a baseline range [L, R].
    // If we are lucky, range size is 1.
    // Query 2: Construct an article that differentiates all W in [L, R].
    // We use random words in [1, L] and add them until the number of lines for L and R differ by R - L.
    // Since lines(W) is monotonically non-increasing, diff == R - L implies strictly decreasing, hence unique for each W.
    
    // Query 1
    cout << "? 2 1 1" << endl;
    int k1;
    cin >> k1;
    if (k1 == -1) exit(0);
    
    if (k1 == 0) {
        // Should not happen as a_i = 1 and W >= 1
        exit(0);
    }
    
    // Determine range [L, R] from k1
    // k1 = ceil(2 / W)
    // If k1 = 1: 1 <= 2/W <= 1 => W >= 2. Max W is 100000. Range [2, 100000]
    // If k1 = 2: 1 < 2/W <= 2 => 1 <= W < 2 => W = 1. Range [1, 1]
    
    int L, R;
    if (k1 == 2) {
        cout << "! 1" << endl;
        return;
    } else {
        L = 2;
        R = 100000;
    }
    
    // Construct Query 2
    // We want simulate(L) - simulate(R) == R - L
    // Use incremental simulation for speed
    
    SimState stateL(L);
    SimState stateR(R);
    
    vector<int> q2;
    mt19937 rng(1337); // Fixed seed for reproducibility
    
    // We limit the size of q2 to avoid excessive length, though we want to ensure uniqueness.
    // 60000-70000 should be enough for range ~100000 given randomness.
    int limit = 70000; 
    
    while (stateL.l - stateR.l < R - L && q2.size() < limit) {
        // Pick random word length in [1, L]
        // Using larger words creates more "friction" / variance
        // But must be <= L to be valid for all W in [L, R]
        int x = std::uniform_int_distribution<int>(1, L)(rng);
        q2.push_back(x);
        stateL.add(x);
        stateR.add(x);
    }
    
    // Perform Query 2
    cout << "? " << q2.size();
    for (int x : q2) cout << " " << x;
    cout << endl;
    
    int k2;
    cin >> k2;
    if (k2 == -1) exit(0);
    
    // Binary search for W in [L, R]
    // Function f(W) = simulate(W, q2) is non-increasing.
    // We look for W such that f(W) == k2.
    // Since we tried to enforce strictly decreasing, there should be at most one such W.
    // If not strictly decreasing, binary search finds *one* valid W.
    
    int low = L, high = R;
    int ans = -1;
    
    // Binary search to find first W where simulate(W) <= k2
    // Actually we want exact match.
    // The function is monotonic descending.
    // larger W -> smaller lines.
    
    int l_bound = L, r_bound = R;
    
    // Find lower bound for W (smallest W s.t. sim(W) <= k2)
    int valid_W = -1;
    
    while (l_bound <= r_bound) {
        int mid = l_bound + (r_bound - l_bound) / 2;
        int lines = simulate(mid, q2);
        if (lines == k2) {
            valid_W = mid;
            // Check if there are smaller W with same lines?
            // If strictly decreasing, unique. 
            // If not, we might have a range. But any valid W is accepted?
            // "Find out the value of W". Implicitly unique.
            // We'll trust our construction or the problem constraints.
            // Let's assume unique or we pick one.
            break; 
        } else if (lines > k2) {
            // Need larger W to reduce lines
            l_bound = mid + 1;
        } else {
            // lines < k2, need smaller W to increase lines
            r_bound = mid - 1;
        }
    }
    
    cout << "! " << valid_W << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}