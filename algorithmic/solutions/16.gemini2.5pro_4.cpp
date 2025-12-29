#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

long long N;

// Function to make a query
long long query(long long x, long long y) {
    if (x == y) return 0;
    cout << "? " << x << " " << y << endl;
    long long dist;
    cin >> dist;
    return dist;
}

// Function to submit the answer
void answer(long long u, long long v) {
    if (u > v) swap(u, v);
    cout << "! " << u << " " << v << endl;
    int r;
    cin >> r;
    if (r == -1) {
        // Exit immediately on wrong answer
        exit(0);
    }
}

// Calculate shortest distance on the original cycle
long long dist_cycle(long long u, long long v) {
    if (u == v) return 0;
    long long diff = abs(u - v);
    return min(diff, N - diff);
}

// Modular addition for 1-based indexing
long long add(long long base, long long offset) {
    long long b = base - 1;
    long long result = (b + offset) % N;
    if (result < 0) {
        result += N;
    }
    return result + 1;
}

// Check if the shortest path is shortened by the chord
bool is_shortened(long long u, long long v) {
    if (u == v) return false;
    return query(u, v) < dist_cycle(u, v);
}

void solve() {
    cin >> N;
    long long m = N / 2;

    // Determine the property P(1) = is_shortened(1, 1+m)
    bool p_ref_val = is_shortened(1, 1 + m);

    // Binary search for the first transition point p1
    long long p1 = -1;
    long long l = 2, r = N;
    while (l <= r) {
        long long mid = l + (r - l) / 2;
        if (is_shortened(mid, add(mid, m)) != p_ref_val) {
            p1 = mid;
            r = mid - 1;
        } else {
            l = mid + 1;
        }
    }

    // First endpoint candidate derived from p1
    long long u_cand1 = add(p1, -1);

    // Binary search for the second transition point p2
    long long p2 = -1;
    l = p1 + 1;
    r = p1 + N - 1;
    bool p_at_p1_val = is_shortened(p1, add(p1, m));
    
    while (l <= r) {
        long long mid_raw = l + (r - l) / 2;
        long long mid = add(1, mid_raw - 1);
        if (is_shortened(mid, add(mid, m)) != p_at_p1_val) {
            p2 = mid;
            r = mid_raw - 1;
        } else {
            l = mid_raw + 1;
        }
    }
    
    // Case: only two transition points, means chord is diametral
    if (p2 == -1) {
        answer(u_cand1, add(u_cand1, m));
        return;
    }

    // Second endpoint candidate derived from p2
    long long u_cand2 = add(p2, -1);
    
    // The endpoints are {u_cand1, u_cand2} or {u_cand1, antipode of u_cand2}
    // Test the first candidate pair
    if (query(u_cand1, u_cand2) == 1) {
        answer(u_cand1, u_cand2);
    } else {
        answer(u_cand1, add(u_cand2, m));
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int T;
    cin >> T;
    while (T--) {
        solve();
    }

    return 0;
}