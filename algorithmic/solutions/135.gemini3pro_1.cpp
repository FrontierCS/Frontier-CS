#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

struct QueryResult {
    int r;
    vector<pair<int, int>> pairs;
};

QueryResult query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    vector<pair<int, int>> pairs(r);
    for (int i = 0; i < r; ++i) {
        cin >> pairs[i].first >> pairs[i].second;
    }
    return {r, pairs};
}

bool is_pair_in_result(const QueryResult& res, int u, int v) {
    if (u > v) swap(u, v);
    for (const auto& p : res.pairs) {
        if (p.first == u && p.second == v) return true;
    }
    return false;
}

int main() {
    int K, N;
    if (!(cin >> K >> N)) return 0;

    vector<int> nodes;
    nodes.reserve(N);
    nodes.push_back(0);
    nodes.push_back(1);
    nodes.push_back(2);

    // Initial sequence [0, 1, 2] is always valid topologically for a triangle
    // (either clockwise or counter-clockwise, which is allowed).

    for (int x = 3; x < N; ++x) {
        int k = nodes.size();
        int start = 0;
        int len = k;

        // Binary search for the slot
        // Slot i corresponds to the gap between nodes[i] and nodes[(i+1)%k]
        while (len > 0) {
            if (len == 1) {
                // Found the slot
                nodes.insert(nodes.begin() + start + 1, x);
                break;
            }

            // Pick pivots to split the current range roughly in half
            int step = len / 4; 
            // Ensure pivots are distinct and useful
            // Pivot indices in the circular buffer
            int idx1 = (start + step) % k;
            int idx2 = (start + len - 1 - step) % k;
            
            // If len is small (2 or 3), step might be 0, handle carefully
            if (len == 2) {
                idx1 = start % k;
                idx2 = (start + 1) % k;
            } else if (len == 3) {
                 idx1 = start % k;
                 idx2 = (start + 1) % k; // adjacent
                 // Better spread for 3: 0 and 1 cover 2 gaps effectively?
                 // Let's stick to formula but ensure distinctness
                 if (idx1 == idx2) idx2 = (idx1 + 1) % k;
            }

            int p1 = nodes[idx1];
            int p2 = nodes[idx2];

            QueryResult res = query(p1, p2, x);

            bool close_p1 = is_pair_in_result(res, min(x, p1), max(x, p1));
            bool close_p2 = is_pair_in_result(res, min(x, p2), max(x, p2));

            if (close_p1 && !close_p2) {
                // Closer to p1, keep first half roughly
                len = (len + 1) / 2;
                // start remains same
            } else if (close_p2 && !close_p1) {
                // Closer to p2, keep second half
                int half = len / 2;
                start = (start + half) % k;
                len = len - half;
            } else {
                // Ambiguous or equidistant.
                // For small ranges, this might happen.
                // Just pick one side to proceed. 
                // Default to first half to ensure progress.
                len = (len + 1) / 2;
            }
        }
    }

    cout << "!";
    for (int i = 0; i < N; ++i) {
        cout << " " << nodes[i];
    }
    cout << endl;

    return 0;
}