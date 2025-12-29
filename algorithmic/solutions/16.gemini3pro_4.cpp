#include <iostream>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <vector>

using namespace std;

long long N;

// Function to calculate cycle distance between two vertices
long long dist_cycle(long long u, long long v) {
    long long diff = abs(u - v);
    return min(diff, N - diff);
}

// Function to get the vertex at 'dist' from 'start' in direction 'dir'
// dir = 1 for "clockwise" (incrementing index), -1 for "counter-clockwise"
long long get_vertex(long long start, long long dist, int dir) {
    long long val = start + dir * dist;
    // Handle modulo arithmetic for 1-based indexing
    val = (val - 1) % N;
    if (val < 0) val += N;
    return val + 1;
}

// Helper for large random numbers
long long rand_large() {
    long long r = 0;
    // Combine multiple rand() calls to cover range up to 10^9
    for(int i=0; i<4; ++i) r = (r << 15) | (rand() & 0x7FFF);
    return abs(r);
}

void solve() {
    cin >> N;
    long long x, y, d_meas;
    long long k = -1;
    long long len_xy = 0;
    int dir = 0;

    // Step 1: Find the chord length k by finding a pair where the chord provides a shortcut.
    // We pick x and y roughly opposite to each other to maximize the probability.
    int tries = 0;
    while (true) {
        x = rand_large() % N + 1;
        long long half = N / 2;
        y = get_vertex(x, half, 1);
        if (x == y) y = (y % N) + 1;

        cout << "? " << x << " " << y << endl;
        cin >> d_meas;
        
        long long d_cyc = dist_cycle(x, y);
        if (d_meas < d_cyc) {
            long long saving = d_cyc - d_meas;
            k = saving + 1;
            len_xy = d_cyc;
            
            // Determine direction from x to y along the shortest cycle path
            long long cw_dist = (y - x + N) % N;
            if (cw_dist == d_cyc) dir = 1;
            else dir = -1;
            break;
        }
        tries++;
        // If we fail too many times, just continue (extremely unlikely)
        if (tries > 200) {
            // Force a retry with different random seed implicitly by continuing loop
        }
    }

    // Step 2: Binary search to find the "transition point" m_star on the path from x to y.
    // m_star is the first vertex on the path such that the distance from x via the chord
    // is shorter than the path along the cycle.
    long long low = 1, high = len_xy;
    long long m_star = len_xy; 

    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (mid <= 0) { low = 1; continue; }
        
        long long vm = get_vertex(x, mid, dir);
        cout << "? " << x << " " << vm << endl;
        long long d_vm;
        cin >> d_vm;
        
        if (d_vm < mid) {
            m_star = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // Step 3: Estimate the position of the chord start u based on m_star.
    // The transition occurs roughly when 2*m > 2*pos_u + k + 1.
    // So pos_u is approximately m_star - k/2.
    // We search a small range around this estimate.
    
    long long approx_pos = m_star - (k + 1) / 2;
    long long start_p = approx_pos - 4;
    long long end_p = approx_pos + 4;
    
    // Clamp search range to valid indices on the path x -> y
    // The chord u must be at a position p such that p >= 0 and p+k <= len_xy.
    if (start_p < 0) start_p = 0;
    if (end_p > len_xy - k) end_p = len_xy - k;
    
    for (long long p = start_p; p <= end_p; ++p) {
        long long u = get_vertex(x, p, dir);
        long long v = get_vertex(x, p + k, dir);
        
        cout << "? " << u << " " << v << endl;
        long long res;
        cin >> res;
        if (res == 1) {
            cout << "! " << u << " " << v << endl;
            int verdict;
            cin >> verdict;
            if (verdict == -1) exit(0);
            return;
        }
    }
}

int main() {
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}