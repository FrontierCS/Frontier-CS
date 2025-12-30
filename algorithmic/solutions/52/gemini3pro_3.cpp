#include <iostream>
#include <vector>
#include <numeric>
#include <deque>
#include <algorithm>

using namespace std;

// Wrapper for query
int query(int l, int r) {
    if (l > r) return 0; 
    if (l == r) return 1;
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

// Wrapper for swap
void do_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    int res;
    cin >> res;
}

// Global mapping p[current_pos] = original_initial_index
vector<int> p;

void perform_swap(int i, int j) {
    if (i == j) return;
    do_swap(i, j);
    swap(p[i], p[j]);
}

// Check if range p[k+1...limit] contains a neighbor of block p[1...k]
// The set p[1...k] is known to be value-contiguous (1 segment).
// We check if adding p[k+1...limit] reduces the segment count relative to separate counts,
// which implies a connection (adjacency in value) exists.
bool check(int k, int limit) {
    if (limit <= k) return false;
    int q_all = query(1, limit);
    int q_part = query(k + 1, limit);
    // Logic:
    // Let S(A) be segments in A. S(A) = 1 for A=p[1..k].
    // S(A U B) = S(A) + S(B) - Connections.
    // Connections = 1 + S(B) - S(A U B) = 1 + q_part - q_all.
    // We want Connections >= 1 => q_part - q_all >= 0 => q_all <= q_part.
    return q_all <= q_part;
}

int main() {
    // Optimize IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, l1, l2;
    if (!(cin >> n >> l1 >> l2)) return 0;

    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }

    p.resize(n + 1);
    iota(p.begin(), p.end(), 0); // p[i] = i initially

    deque<int> chain;
    chain.push_back(p[1]);
    bool tail_at_k = true; // Indicates if chain.back() is physically at p[k]

    for (int k = 1; k < n; ++k) {
        // Binary search for neighbor in [k+1, n]
        int lo = k + 1, hi = n;
        int found_idx = -1;
        
        while (lo <= hi) {
            if (lo == hi) {
                found_idx = lo;
                break;
            }
            int mid = lo + (hi - lo) / 2;
            if (check(k, mid)) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        found_idx = lo;

        perform_swap(k + 1, found_idx);
        
        // Check connection with p[k]
        // p[k] is the element at position k, which is one of the endpoints of the chain.
        int q = query(k, k + 1);
        int u = p[k + 1]; // This is the original index of the element now at k+1
        
        if (q == 1) {
            // Connected to p[k]
            // If p[k] was the tail, u becomes the new tail.
            // If p[k] was the front, u becomes the new front.
            if (tail_at_k) {
                chain.push_back(u);
                tail_at_k = true; // u is at k+1, so tail is at k+1
            } else {
                chain.push_front(u);
                tail_at_k = false; // u is at k+1, so front is at k+1
            }
        } else {
            // Not connected to p[k], so it must be connected to the OTHER endpoint.
            if (tail_at_k) {
                // p[k] was tail. u connects to head.
                chain.push_front(u);
                tail_at_k = false; // u is at k+1, so front is at k+1
            } else {
                // p[k] was front. u connects to tail.
                chain.push_back(u);
                tail_at_k = true; // u is at k+1, so tail is at k+1
            }
        }
    }

    // Construct answer
    // 'chain' contains the original indices in the order of their values (monotonic)
    vector<int> ans(n + 1);
    int val = 1;
    for (int idx : chain) {
        ans[idx] = val++;
    }

    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}