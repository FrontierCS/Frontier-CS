#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Function to perform a query
// Prints the query in the specified format and reads the result.
long long ask(const vector<int>& left, const vector<int>& right) {
    cout << "? " << left.size() << " " << right.size() << endl;
    for (size_t i = 0; i < left.size(); ++i) {
        cout << left[i] << (i == left.size() - 1 ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < right.size(); ++i) {
        cout << right[i] << (i == right.size() - 1 ? "" : " ");
    }
    cout << endl;
    
    long long response;
    cin >> response;
    // If input fails (e.g. if the judge terminates the program), exit gracefully.
    if (cin.fail()) exit(0); 
    return response;
}

void solve() {
    int n;
    cin >> n;
    if (cin.fail()) return;

    // Phase 1: Scan to find the second charged magnet.
    // We maintain a prefix set {1, ..., i} and query it against {i+1}.
    // Since there are at least two charged magnets, eventually:
    // 1. The prefix sum will be non-zero (meaning it contains the first charged magnet).
    // 2. The magnet (i+1) will be non-zero (meaning it is the second charged magnet).
    // The query result is product of sums. When it becomes non-zero, we found the split.
    // Crucially, until we find the second charged magnet, the prefix sum has magnitude at most 1,
    // so we never crash the machine (force never exceeds 1 in magnitude).
    int second_charged = -1;
    vector<int> prefix;
    for (int i = 1; i < n; ++i) {
        prefix.push_back(i);
        long long res = ask(prefix, {i + 1});
        if (res != 0) {
            second_charged = i + 1;
            break;
        }
    }

    // Phase 2: Binary search to locate the first charged magnet within [1, second_charged - 1].
    // Since the scan stopped at second_charged, the range [1, second_charged - 1] contains exactly 
    // one charged magnet. We binary search for it by querying a subset against the known 
    // charged magnet 'second_charged'.
    int l = 1, r = second_charged - 1;
    while (l < r) {
        int mid = l + (r - l) / 2;
        vector<int> subset;
        for (int i = l; i <= mid; ++i) subset.push_back(i);
        
        // Query subset [l, mid] against {second_charged}
        // If non-zero, the charged magnet is in [l, mid].
        // Otherwise, it is in [mid+1, r].
        long long res = ask(subset, {second_charged});
        if (res != 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    int first_charged = l;

    // Phase 3: Identify the type of the remaining magnets (from second_charged + 1 to n).
    // We can simply test each remaining magnet against a known charged magnet (e.g., second_charged).
    // This is safe because sum of one charged magnet is +/- 1, and testing against unknown gives product in {-1, 0, 1}.
    vector<bool> is_demagnetized(n + 1, true);
    is_demagnetized[first_charged] = false;
    is_demagnetized[second_charged] = false;

    for (int i = second_charged + 1; i <= n; ++i) {
        long long res = ask({second_charged}, {i});
        if (res != 0) {
            is_demagnetized[i] = false;
        }
    }

    // Collect all demagnetized indices and print the answer
    vector<int> result;
    for (int i = 1; i <= n; ++i) {
        if (is_demagnetized[i]) {
            result.push_back(i);
        }
    }

    cout << "! " << result.size();
    for (int idx : result) {
        cout << " " << idx;
    }
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}