#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <random>

using namespace std;

// Structure to hold pair response
struct Pair {
    int u, v;
    bool operator==(const Pair& other) const {
        return (u == other.u && v == other.v) || (u == other.v && v == other.u);
    }
};

// Helper to check if a specific pair exists in the response
bool has_pair(const vector<Pair>& res, int u, int v) {
    for (const auto& p : res) {
        if ((p.u == u && p.v == v) || (p.u == v && p.v == u)) return true;
    }
    return false;
}

// Function to perform a query
vector<Pair> query(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    int r;
    cin >> r;
    vector<Pair> res(r);
    for (int i = 0; i < r; ++i) {
        cin >> res[i].u >> res[i].v;
    }
    return res;
}

// Global list of doors in current cyclic order
vector<int> doors;

// Returns the index in 'doors' that is closest to 'target'
int find_closest(int target) {
    int sz = doors.size();
    if (sz == 0) return -1;
    if (sz == 1) return 0;

    int L = 0;
    int current_sz = sz;

    // Binary/Ternary search on the cycle to narrow down the closest element
    while (current_sz > 3) {
        int m1_offset = current_sz / 3;
        int m2_offset = (2 * current_sz) / 3;
        
        int idx1 = (L + m1_offset) % sz;
        int idx2 = (L + m2_offset) % sz;
        
        vector<Pair> res = query(doors[idx1], doors[idx2], target);
        
        bool p1_close = has_pair(res, doors[idx1], target);
        bool p2_close = has_pair(res, doors[idx2], target);
        
        if (p1_close && p2_close) {
            // Target is equidistant to idx1 and idx2.
            // It lies on the bisector.
            // Discard the "outer" halves, keep range between m1 and m2 roughly.
            // Or just treat as p1_close to simplify (reduce right side).
            // Keeping [L, m2] is safe.
            // Actually, if equidistant, the closest point in our set is likely between them.
            // We can just proceed with p1_close logic.
            p2_close = false; 
        }

        if (p1_close) {
            // Target is closer to idx1 than idx2.
            // We can discard the segment around idx2 (the far side).
            // Geometric bisector is at (m1 + m2) / 2.
            // We keep [L, bisector].
            int limit_offset = (m1_offset + m2_offset) / 2 + 1;
            current_sz = limit_offset; 
        } else if (p2_close) {
            // Target is closer to idx2.
            // Discard [L, bisector]. Keep [bisector, End].
            int start_offset = (m1_offset + m2_offset) / 2;
            L = (L + start_offset) % sz;
            current_sz = current_sz - start_offset;
        } else {
            // {idx1, idx2} closest. Target is far from both.
            // Target is in the "outer" region: [L, idx1] U [idx2, End]
            // We query the boundaries to see which side.
            int idxL = L;
            int end_offset = current_sz - 1;
            int idxR = (L + end_offset) % sz;
            
            vector<Pair> res2 = query(doors[idxL], doors[idxR], target);
            if (has_pair(res2, doors[idxL], target)) {
                // Closer to L. Keep [L, m1].
                current_sz = m1_offset + 1;
            } else if (has_pair(res2, doors[idxR], target)) {
                // Closer to R. Keep [m2, End].
                L = idx2;
                current_sz = current_sz - m2_offset;
            } else {
                // Should not happen if target is in range.
                // Fallback: just linear scan what we have.
                break;
            }
        }
    }

    // Linear scan remaining candidates using a tournament
    vector<int> candidates;
    for(int k=0; k<current_sz; ++k) candidates.push_back((L + k) % sz);
    
    while(candidates.size() > 1) {
        vector<int> next_gen;
        for(size_t i=0; i+1 < candidates.size(); i+=2) {
            int u = candidates[i];
            int v = candidates[i+1];
            vector<Pair> r = query(doors[u], doors[v], target);
            if (has_pair(r, doors[u], target)) next_gen.push_back(u); 
            else if (has_pair(r, doors[v], target)) next_gen.push_back(v);
            else next_gen.push_back(u); // Fallback
        }
        if(candidates.size() % 2 == 1) next_gen.push_back(candidates.back());
        candidates = next_gen;
    }
    return candidates[0];
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int K, N;
    if (!(cin >> K >> N)) return 0;

    vector<int> p(N);
    for (int i = 0; i < N; ++i) p[i] = i;

    // Shuffle to ensure random insertion order (avoid worst cases)
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);

    // Initial pair
    doors.push_back(p[0]);
    doors.push_back(p[1]);

    // Insert remaining doors one by one
    for (int i = 2; i < N; ++i) {
        int target = p[i];
        
        // Find the existing door closest to the target
        int closest_idx = find_closest(target);
        
        // Determine insertion position relative to closest_idx
        int sz = doors.size();
        int u = doors[closest_idx];
        int prev = doors[(closest_idx - 1 + sz) % sz];
        int next = doors[(closest_idx + 1) % sz];

        // Query neighbors to find exact spot
        vector<Pair> res = query(doors[prev], doors[next], target);
        bool c_prev = has_pair(res, doors[prev], target);
        bool c_next = has_pair(res, doors[next], target);
        
        if (c_prev && c_next) {
            // Target is roughly equidistant to prev and next, meaning it's very close to u.
            // Check relative to u to disambiguate.
             vector<Pair> r2 = query(doors[prev], u, target);
             if (has_pair(r2, doors[prev], target)) {
                 // Closer to prev than u? No, closer to prev than u is to prev?
                 // No, query is {prev, u, target}.
                 // If {prev, target} is returned, it means d(prev, target) <= d(prev, u).
                 // Since target is between prev and u, this means target is "before" u.
                 doors.insert(doors.begin() + closest_idx, target);
             } else {
                 // {u, target} or {prev, u} returned (target is closer to u or far).
                 // Since target is close to u, it's likely {u, target}.
                 // This implies d(u, target) <= d(prev, target).
                 // This alone doesn't strictly say "after", but combined with c_next being true
                 // and the geometry, it usually means we check the other side.
                 // Actually, simpler logic:
                 // {prev, target} -> target is in (prev, u).
                 // else -> target is in (u, next).
                 if (closest_idx + 1 == sz) doors.push_back(target);
                 else doors.insert(doors.begin() + closest_idx + 1, target);
             }
        } else if (c_prev) {
            doors.insert(doors.begin() + closest_idx, target);
        } else {
            if (closest_idx + 1 == sz) doors.push_back(target);
            else doors.insert(doors.begin() + closest_idx + 1, target);
        }
    }

    // Output result
    cout << "!";
    for (int x : doors) cout << " " << x;
    cout << endl;

    return 0;
}