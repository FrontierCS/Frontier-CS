#include <iostream>
#include <vector>
#include <cassert>
using namespace std;

int main() {
    int n;
    cin >> n;

    if (n == 2) {
        // only one possible permutation with p1 <= 1
        cout << "! 1 2" << endl;
        cout.flush();
        return 0;
    }

    vector<int> ans(n + 1, 0); // 1-indexed

    // Step 1: find candidates for 1 and n (positions where query of size n-1 returns 1)
    vector<int> is_cand(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        cout << "? " << n - 1;
        for (int j = 1; j <= n; ++j) if (j != i) cout << " " << j;
        cout << endl;
        cout.flush();
        int r;
        cin >> r;
        if (r == 1) is_cand[i] = 1;
    }

    vector<int> cands;
    for (int i = 1; i <= n; ++i) if (is_cand[i]) cands.push_back(i);
    int c1 = cands[0], c2 = cands[1];
    // assume c1 corresponds to value 1, c2 to value n
    ans[c1] = 1;
    ans[c2] = n;

    // Step 2: determine parity of each position relative to c1
    vector<int> parity(n + 1, 0); // 1 = odd, 0 = even
    parity[c1] = 1;
    for (int i = 1; i <= n; ++i) {
        if (i == c1) continue;
        cout << "? 2 " << c1 << " " << i << endl;
        cout.flush();
        int r;
        cin >> r;
        parity[i] = (r == 1) ? 1 : 0;
    }

    // Build lists of odd and even indices
    vector<int> O, E;
    for (int i = 1; i <= n; ++i) {
        if (parity[i] == 1) O.push_back(i);
        else E.push_back(i);
    }

    // Precompute sums of all odd and all even numbers
    int half = n / 2;
    long long sumOdd = (long long)half * half;               // sum of 1,3,5,...,n-1
    long long sumEven = (long long)half * (half + 1);        // sum of 2,4,6,...,n

    // Helper function to ask a query given a vector of indices
    auto ask_query = [&](const vector<int>& idx) {
        cout << "? " << idx.size();
        for (int x : idx) cout << " " << x;
        cout << endl;
        cout.flush();
        int res;
        cin >> res;
        return res;
    };

    // Step 3: determine odd values (except c1)
    for (int j : O) {
        if (j == c1) continue;

        // Query 1: O \ {j}
        vector<int> set1;
        for (int x : O) if (x != j) set1.push_back(x);
        int k1 = set1.size();
        int ans1 = ask_query(set1);

        // Query 2: O \ {j, c1} if possible (size >= 1)
        int ans2 = -1;
        if (k1 > 1) { // implies |O| >= 3, so after removing j and c1 at least one remains
            vector<int> set2;
            for (int x : O) if (x != j && x != c1) set2.push_back(x);
            if (!set2.empty()) ans2 = ask_query(set2);
        }

        // Query 3: {c1, c2, j}
        vector<int> set3 = {c1, c2, j};
        int ans3 = ask_query(set3);

        // Find the odd value v in {3,5,...,n-1} that matches the answers
        int found = -1;
        for (int v = 3; v <= n - 1; v += 2) {
            int exp1 = ((sumOdd - v) % k1 == 0) ? 1 : 0;
            bool ok = (exp1 == ans1);
            if (ans2 != -1) {
                int k2 = O.size() - 2; // because we removed j and c1
                int exp2 = ((sumOdd - v - 1) % k2 == 0) ? 1 : 0;
                ok = ok && (exp2 == ans2);
            }
            int exp3 = ((1 + n + v) % 3 == 0) ? 1 : 0;
            ok = ok && (exp3 == ans3);
            if (ok) {
                found = v;
                break;
            }
        }
        assert(found != -1);
        ans[j] = found;
    }

    // Step 4: determine even values (except c2)
    for (int j : E) {
        if (j == c2) continue;

        // Query 1: E \ {j}
        vector<int> set1;
        for (int x : E) if (x != j) set1.push_back(x);
        int k1 = set1.size();
        int ans1 = ask_query(set1);

        // Query 2: E \ {j, c2} if possible
        int ans2 = -1;
        if (k1 > 1) {
            vector<int> set2;
            for (int x : E) if (x != j && x != c2) set2.push_back(x);
            if (!set2.empty()) ans2 = ask_query(set2);
        }

        // Query 3: {c1, c2, j}
        vector<int> set3 = {c1, c2, j};
        int ans3 = ask_query(set3);

        // Find the even value v in {2,4,...,n-2} that matches
        int found = -1;
        for (int v = 2; v <= n - 2; v += 2) {
            int exp1 = ((sumEven - v) % k1 == 0) ? 1 : 0;
            bool ok = (exp1 == ans1);
            if (ans2 != -1) {
                int k2 = E.size() - 2; // because we removed j and c2
                int exp2 = ((sumEven - v - n) % k2 == 0) ? 1 : 0;
                ok = ok && (exp2 == ans2);
            }
            int exp3 = ((1 + n + v) % 3 == 0) ? 1 : 0;
            ok = ok && (exp3 == ans3);
            if (ok) {
                found = v;
                break;
            }
        }
        assert(found != -1);
        ans[j] = found;
    }

    // Step 5: adjust if needed so that ans[1] <= n/2
    if (ans[1] > n / 2) {
        for (int i = 1; i <= n; ++i) {
            ans[i] = n + 1 - ans[i];
        }
    }

    // Output the guess
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << ans[i];
    cout << endl;
    cout.flush();

    return 0;
}