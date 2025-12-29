#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int N;
int current_count = 0;

int query(int x) {
    cout << "? " << x << "\n";
    cout.flush();
    int r;
    cin >> r;
    current_count = r;
    return r;
}

void answer(int a, int b) {
    cout << "! " << a << " " << b << "\n";
    cout.flush();
}

// Global buffer to store answers
vector<pair<int, int>> pairs;

// States for recursion
// Solve_II: A is IN, B is IN
// Solve_OO: A is OUT, B is OUT
// Solve_IO: A is IN, B is OUT (symmetric to OI)

void Solve_II(vector<int>& A, vector<int>& B);
void Solve_OO(vector<int>& A, vector<int>& B);
void Solve_IO(vector<int>& A, vector<int>& B);

void Solve_II(vector<int>& A, vector<int>& B) {
    if (A.empty()) return;
    if (A.size() == 1) {
        pairs.push_back({A[0], B[0]});
        return;
    }

    int half = A.size() / 2;
    vector<int> A1(A.begin(), A.begin() + half);
    vector<int> A2(A.begin() + half, A.end());
    
    // A1 to OUT
    for (int x : A1) query(x);

    // Current state: A1 OUT, A2 IN. B IN.
    // Scan B: toggle to OUT
    vector<int> B1, B2;
    // Optimization: if we fill one bucket, the rest go to the other.
    // But we need B to be OUT at the end.
    // So we must toggle everyone in B.
    // However, we can deduce mapping without reading result if one bucket full?
    // No, we need to toggle anyway. The query result is "free" with the toggle.
    
    for (int x : B) {
        int r = query(x); 
        // Before: x IN. A1 OUT, A2 IN.
        // After: x OUT.
        // If partner in A1 (OUT): x OUT, p OUT -> was 0, now 0? 
        // Wait. Before x OUT: x IN, p OUT. Mineral present (x).
        // After x OUT: x OUT, p OUT. Mineral absent. Count drops.
        
        // If partner in A2 (IN): x IN, p IN. Mineral present.
        // After x OUT: x OUT, p IN. Mineral present (p). Count stable.
        
        // But we must track delta. current_count is updated by query.
        // We need to know previous count? No, query returns CURRENT count.
        // Let's deduce from expected behavior.
        // We can't easily know previous count unless we track it globally or pass it.
        // But we know 'r'.
        // Wait, other pairs might be affecting count?
        // No, A and B are partitioned. A1, A2, B1, B2 are the only active things.
        // Actually, we need to be careful about "Count drops".
        // Instead of tracking delta, let's use the property:
        // A1 OUT, A2 IN.
        // If match A1: removing B reduces count (Active -> Inactive).
        // If match A2: removing B keeps count (Active -> Active via partner).
        // But removing B might drop count for OTHER reasons? No.
        
        // Actually, logic:
        // Case 1: p in A1 (OUT). x IN -> OUT. Mineral was Present -> Absent. Count decreases.
        // Case 2: p in A2 (IN). x IN -> OUT. Mineral was Present -> Present. Count same.
        // We can distinguish by checking if count decreased relative to BEFORE this query.
        // But we need 'prev_r'.
        // Since we toggle sequentially, 'prev_r' changes.
        // BUT, notice:
        // In Case 1, count decreases by 1.
        // In Case 2, count same.
        // So we can just checking relation between r and prev_r.
    }
    
    // To do this correctly, we need to re-run the loop with logic
    // We cannot restart loop. We need to implement logic inside loop.
    // We need 'prev_r'. 'current_count' is global and updated.
    // BUT we need value BEFORE query.
    // We can store temp.
    
    // Reset B1, B2
    B1.clear(); B2.clear();
    
    // We need to restore A and B logic, so let's just redo the loop structure
    // Since we consumed B in the logic above, let's write it properly.
    
    // Correct loop:
    int prev_c = current_count; // Count after A1 toggled OUT
    // Wait, I toggled A1 above but didn't update prev_c properly?
    // current_count is updated by query(x). So it is correct.
    
    for (int x : B) {
        int before = current_count;
        query(x); // toggles x OUT
        int after = current_count;
        
        if (after < before) {
            // Count dropped implies partner was OUT (A1)
            B1.push_back(x);
        } else {
            // Count same (or increased? shouldn't increase) implies partner was IN (A2)
            B2.push_back(x);
        }
    }
    
    // State: A1 OUT, A2 IN. B OUT (B1 U B2).
    // Recurse (A1, B1) -> Solve_OO
    Solve_OO(A1, B1);
    
    // Recurse (A2, B2) -> Solve_IO (A2 IN, B2 OUT)
    Solve_IO(A2, B2);
}

void Solve_OO(vector<int>& A, vector<int>& B) {
    if (A.empty()) return;
    if (A.size() == 1) {
        pairs.push_back({A[0], B[0]});
        return;
    }
    
    int half = A.size() / 2;
    vector<int> A1(A.begin(), A.begin() + half);
    vector<int> A2(A.begin() + half, A.end());
    
    // Toggle A1 IN
    for (int x : A1) query(x);
    
    // State: A1 IN, A2 OUT. B OUT.
    // Toggle B IN
    vector<int> B1, B2;
    for (int x : B) {
        int before = current_count;
        query(x); // toggles x IN
        int after = current_count;
        
        // x OUT -> IN.
        // If p in A1 (IN): Pair forms. Mineral already present (p). Count same.
        // If p in A2 (OUT): Mineral becomes present (x). Count increases.
        
        if (after > before) {
            // Partner in A2
            B2.push_back(x);
        } else {
            // Partner in A1
            B1.push_back(x);
        }
    }
    
    // State: A1 IN, A2 OUT. B IN.
    // Recurse (A1, B1) -> Solve_II
    Solve_II(A1, B1);
    
    // Recurse (A2, B2) -> B2 IN, A2 OUT -> Solve_IO(B2, A2) (swapped)
    Solve_IO(B2, A2);
}

void Solve_IO(vector<int>& A, vector<int>& B) {
    // A IN, B OUT
    if (A.empty()) return;
    if (A.size() == 1) {
        pairs.push_back({A[0], B[0]});
        return;
    }
    
    int half = A.size() / 2;
    vector<int> A1(A.begin(), A.begin() + half);
    vector<int> A2(A.begin() + half, A.end());
    
    // Toggle A1 OUT
    for (int x : A1) query(x);
    
    // State: A1 OUT, A2 IN. B OUT.
    // Toggle B IN
    vector<int> B1, B2;
    for (int x : B) {
        int before = current_count;
        query(x); // toggles x IN
        int after = current_count;
        
        // x OUT -> IN
        // If p in A1 (OUT): x new. Count increases.
        // If p in A2 (IN): Pair forms. Count same.
        
        if (after > before) {
            // Partner in A1
            B1.push_back(x);
        } else {
            // Partner in A2
            B2.push_back(x);
        }
    }
    
    // State: A1 OUT, A2 IN. B IN.
    // Recurse (A1, B1) -> B1 IN, A1 OUT -> Solve_IO(B1, A1)
    Solve_IO(B1, A1);
    
    // Recurse (A2, B2) -> A2 IN, B2 IN -> Solve_II(A2, B2)
    Solve_II(A2, B2);
}

int main() {
    // Optimized IO
    // interactive, so cin/cout is tied, but sync false helps
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> N)) return 0;
    
    vector<int> A, B;
    A.reserve(N);
    B.reserve(N);
    
    // Initial Phase: Partition into A and B
    for (int i = 1; i <= 2 * N; ++i) {
        int before = current_count;
        query(i);
        int after = current_count;
        
        if (after > before) {
            // New mineral, keep in device
            A.push_back(i);
        } else {
            // Pair formed with something in A
            // Keep in device (don't remove!) to satisfy Start State of Solve_II
            B.push_back(i);
        }
    }
    
    // Start recursion. A and B are both IN.
    Solve_II(A, B);
    
    for (auto& p : pairs) {
        answer(p.first, p.second);
    }
    
    return 0;
}