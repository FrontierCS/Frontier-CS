#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Global variables to store problem dimensions and auxiliary structures
int N, M;
vector<int> is_removed;
vector<int> complement_buf;
vector<vector<int>> answers;

// Perform a query to the interactor
int query(const vector<int>& subset) {
    if (subset.empty()) return 0;
    cout << "? " << subset.size();
    for (int x : subset) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Check if adding 'candidates' to 'accepted' still allows the set to fit within 'W' buckets.
// Fitting in W buckets means for every color, the count is <= W.
// This is equivalent to checking if U \ (accepted U candidates) can form at least M - W sticks.
bool check(const vector<int>& accepted, const vector<int>& candidates, int W) {
    // Mark elements as removed from U
    for (int x : accepted) is_removed[x] = 1;
    for (int x : candidates) is_removed[x] = 1;
    
    // Construct the complement set
    complement_buf.clear();
    for (int i = 1; i <= N * M; ++i) {
        if (!is_removed[i]) {
            complement_buf.push_back(i);
        }
    }
    
    int res = 0;
    // If complement is empty, we can form 0 sticks.
    if (!complement_buf.empty()) {
        res = query(complement_buf);
    }
    
    // Unmark elements
    for (int x : accepted) is_removed[x] = 0;
    for (int x : candidates) is_removed[x] = 0;
    
    return res >= M - W;
}

// Greedily distribute candidates into accepted (Left side) and rejected (Right side)
void distribute(const vector<int>& candidates, vector<int>& accepted, vector<int>& rejected, int W) {
    if (candidates.empty()) return;
    
    // Optimization: If accepted set is already full (contains N*W elements),
    // any further elements must be rejected.
    if (accepted.size() == (size_t)N * W) {
        rejected.insert(rejected.end(), candidates.begin(), candidates.end());
        return;
    }

    // If the entire batch of candidates fits, accept them all
    if (check(accepted, candidates, W)) {
        accepted.insert(accepted.end(), candidates.begin(), candidates.end());
        return;
    }
    
    // If a single candidate fails, it must be rejected
    if (candidates.size() == 1) {
        rejected.push_back(candidates[0]);
        return;
    }
    
    // Split candidates and recurse
    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());
    
    distribute(left_part, accepted, rejected, W);
    distribute(right_part, accepted, rejected, W);
}

// Recursive function to solve for bucket range [L, R]
void solve(vector<int>& p, int L, int R) {
    if (L == R) {
        answers[L] = p;
        return;
    }
    
    int mid = (L + R) / 2;
    int W = mid - L + 1; // Width of the left half
    
    vector<int> accepted;
    vector<int> rejected;
    accepted.reserve(p.size());
    rejected.reserve(p.size());
    
    // Partition p into accepted (for buckets [L, mid]) and rejected (for [mid+1, R])
    distribute(p, accepted, rejected, W);
    
    solve(accepted, L, mid);
    solve(rejected, mid + 1, R);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    // Special case M=1: All dangos form a single stick
    if (M == 1) {
        cout << "! ";
        for (int i = 1; i <= N; ++i) cout << i << (i == N ? "" : " ");
        cout << endl;
        return 0;
    }
    
    // Initialize global structures
    is_removed.resize(N * M + 1, 0);
    complement_buf.reserve(N * M);
    answers.resize(M + 1);
    
    vector<int> p(N * M);
    iota(p.begin(), p.end(), 1);
    
    // Random shuffle is crucial for efficiency
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);
    
    // Solve recursively
    solve(p, 1, M);
    
    // Output answers
    for (int i = 1; i <= M; ++i) {
        cout << "!";
        for (int x : answers[i]) {
            cout << " " << x;
        }
        cout << endl;
    }
    
    return 0;
}