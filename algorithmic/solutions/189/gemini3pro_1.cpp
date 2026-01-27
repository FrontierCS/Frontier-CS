#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <tuple>

using namespace std;

// Fast I/O to handle large input/output efficiently
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Constants
const int K = 10; // Anchor length for k-mer matching

// Hashing types and constants
typedef unsigned long long ull;
const ull BASE = 37;

// Map characters [0-9, A-Z] to [0-35]
inline int get_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Struct for hash information
struct HashInfo {
    ull h;
    int id;
};

// Comparator for sorting HashInfo
bool compareHashInfo(const HashInfo& a, const HashInfo& b) {
    if (a.h != b.h) return a.h < b.h;
    return a.id < b.id;
}

// Greedy alignment for gap regions with limited lookahead
// Priority: Match > Sync (Delete/Insert) > Substitute
string solve_gap(const string& s1, int start1, int end1, const string& s2, int start2, int end2) {
    string res;
    int len1 = end1 - start1;
    int len2 = end2 - start2;
    res.reserve(max(len1, len2) + 64);

    int i = 0;
    int j = 0;
    int lookahead = 10; 

    while (i < len1 && j < len2) {
        char c1 = s1[start1 + i];
        char c2 = s2[start2 + j];

        if (c1 == c2) {
            res += 'M';
            i++;
            j++;
        } else {
            // Mismatch: Check for potential re-synchronization within lookahead
            int best_op = 0; // 0: Sub/Mismatch, 1: Del, 2: Ins
            int best_k = 0;
            
            // Check for match after deleting k chars from s1
            for (int k = 1; k <= lookahead && i + k < len1; ++k) {
                if (s1[start1 + i + k] == c2) {
                    // Check next character to confirm stability of sync
                    bool good = true;
                    if (i + k + 1 < len1 && j + 1 < len2) {
                        if (s1[start1 + i + k + 1] != s2[start2 + j + 1]) good = false;
                    }
                    if (good) {
                        best_op = 1;
                        best_k = k;
                        goto APPLY;
                    }
                }
            }
            
            // Check for match after inserting k chars (skipping k in s2)
            for (int k = 1; k <= lookahead && j + k < len2; ++k) {
                if (c1 == s2[start2 + j + k]) {
                    bool good = true;
                    if (i + 1 < len1 && j + k + 1 < len2) {
                        if (s1[start1 + i + 1] != s2[start2 + j + k + 1]) good = false;
                    }
                    if (good) {
                        best_op = 2;
                        best_k = k;
                        goto APPLY;
                    }
                }
            }

            APPLY:
            if (best_op == 1) {
                for(int x=0; x<best_k; ++x) res += 'D';
                i += best_k;
            } else if (best_op == 2) {
                for(int x=0; x<best_k; ++x) res += 'I';
                j += best_k;
            } else {
                // Substitute (Cost 1)
                res += 'M';
                i++;
                j++;
            }
        }
    }

    // Handle remaining characters
    while (i < len1) { res += 'D'; i++; }
    while (j < len2) { res += 'I'; j++; }

    return res;
}

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = s1.length();
    int m = s2.length();

    // If strings are too short for anchoring, solve directly
    if (n < K || m < K) {
        cout << solve_gap(s1, 0, n, s2, 0, m) << endl;
        return 0;
    }

    // --- Step 1: Collect unique K-mers from S1 ---
    vector<HashInfo> v1;
    v1.reserve(n - K + 1);
    
    ull h = 0;
    ull power = 1;
    
    for(int i=0; i<K-1; ++i) power *= BASE;

    // Rolling hash for S1
    for(int i=0; i<n; ++i) {
        if (i >= K) h = h - get_val(s1[i-K]) * power;
        h = h * BASE + get_val(s1[i]);
        if (i >= K - 1) v1.push_back({h, i - K + 1});
    }

    sort(v1.begin(), v1.end(), compareHashInfo);

    // Filter to keep only unique hashes in S1
    vector<HashInfo> u1;
    u1.reserve(v1.size());
    for(size_t i=0; i<v1.size(); ) {
        size_t j = i + 1;
        while(j < v1.size() && v1[j].h == v1[i].h) j++;
        if(j == i + 1) u1.push_back(v1[i]);
        i = j;
    }
    vector<HashInfo>().swap(v1); // Free memory

    // --- Step 2: Collect unique K-mers from S2 ---
    vector<HashInfo> v2;
    v2.reserve(m - K + 1);
    h = 0;
    for(int i=0; i<m; ++i) {
        if (i >= K) h = h - get_val(s2[i-K]) * power;
        h = h * BASE + get_val(s2[i]);
        if (i >= K - 1) v2.push_back({h, i - K + 1});
    }

    sort(v2.begin(), v2.end(), compareHashInfo);

    // --- Step 3: Find Anchors (Intersection of unique K-mers) ---
    vector<pair<int, int>> anchors;
    anchors.reserve(min(u1.size(), v2.size()) / 2);

    size_t p1 = 0;
    size_t i = 0;
    // Both u1 and v2 are sorted by hash. Iterate to find matches.
    while(i < v2.size() && p1 < u1.size()) {
        size_t j = i + 1;
        while(j < v2.size() && v2[j].h == v2[i].h) j++;
        
        if (j == i + 1) { // Unique in S2
            ull h2 = v2[i].h;
            // Advance p1 to match hash
            while(p1 < u1.size() && u1[p1].h < h2) p1++;
            if (p1 < u1.size() && u1[p1].h == h2) {
                // Match found
                anchors.push_back({u1[p1].id, v2[i].id});
                p1++;
            }
        }
        i = j;
    }
    
    // Clean up memory
    vector<HashInfo>().swap(v2);
    vector<HashInfo>().swap(u1);

    // --- Step 4: Longest Chain of Anchors (LIS) ---
    if (anchors.empty()) {
        cout << solve_gap(s1, 0, n, s2, 0, m) << endl;
        return 0;
    }

    // Sort anchors by position in S1
    sort(anchors.begin(), anchors.end());

    // LIS on position in S2
    vector<int> tails; 
    vector<int> parent(anchors.size(), -1);
    
    for(size_t k=0; k<anchors.size(); ++k) {
        int r = anchors[k].second;
        // Find position to extend
        auto it = lower_bound(tails.begin(), tails.end(), r, [&](int idx, int val){
            return anchors[idx].second < val;
        });
        if (it == tails.end()) {
            if (!tails.empty()) parent[k] = tails.back();
            tails.push_back(k);
        } else {
            if (it != tails.begin()) parent[k] = *prev(it);
            *it = k;
        }
    }

    // Reconstruct path
    vector<pair<int, int>> path;
    int curr = tails.empty() ? -1 : tails.back();
    while(curr != -1) {
        path.push_back(anchors[curr]);
        curr = parent[curr];
    }
    reverse(path.begin(), path.end());

    // --- Step 5: Construct Transcript ---
    string transcript;
    transcript.reserve(max(n, m) + 1024);

    int cx = 0, cy = 0;
    
    for (auto& p : path) {
        int nx = p.first;
        int ny = p.second;
        
        // Gap from current pos to anchor start
        int gap1 = max(0, nx - cx);
        int gap2 = max(0, ny - cy);
        
        if (gap1 > 0 || gap2 > 0) {
            transcript += solve_gap(s1, cx, cx + gap1, s2, cy, cy + gap2);
            cx += gap1;
            cy += gap2;
        }

        // Inside anchor (handle potential overlaps if anchors are dense)
        int end_anchor_x = nx + K;
        int end_anchor_y = ny + K;
        
        // If anchors overlap, we only output 'M' for the new matching part
        int len_x = max(0, end_anchor_x - cx);
        int len_y = max(0, end_anchor_y - cy);
        int len = min(len_x, len_y);
        
        for(int k=0; k<len; ++k) transcript += 'M';
        
        cx += len;
        cy += len;
    }

    // Final gap
    transcript += solve_gap(s1, cx, n, s2, cy, m);

    cout << transcript << endl;

    return 0;
}