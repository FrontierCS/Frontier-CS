#include <bits/stdc++.h>
using namespace std;

struct InteractiveSolver {
    int n;
    unordered_map<string, int> cache;
    int queryCount = 0;
    static constexpr int QUERY_LIMIT = 3500;

    int ask(const string &s) {
        auto it = cache.find(s);
        if (it != cache.end()) return it->second;

        ++queryCount;
        if (queryCount > QUERY_LIMIT) {
            // Exceeded query limit; in an actual interactive environment this would be invalid.
            // Exit to avoid undefined behavior.
            exit(0);
        }

        cout << "? " << s << '\n' << flush;

        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);

        cache.emplace(s, ans);
        return ans;
    }

    string buildMaskFromIndices(const vector<int> &idx) {
        string s(n, '0');
        for (int v : idx) s[v] = '1';
        return s;
    }

    bool intersectNonEmpty(const string &A_str, int sizeA, int neighA, const vector<int> &B_idx) {
        if (B_idx.empty()) return false;

        const int sizeB = (int)B_idx.size();

        string B_str = buildMaskFromIndices(B_idx);
        int qB = ask(B_str);
        int neighB = sizeB + qB;

        string AU_str = A_str;
        for (int v : B_idx) AU_str[v] = '1';
        int qAU = ask(AU_str);
        int neighAU = (sizeA + sizeB) + qAU;

        int inter = neighA + neighB - neighAU;
        return inter > 0;
    }

    int findOneCandidate(const string &A_str, int sizeA, int neighA, vector<int> cand) {
        while ((int)cand.size() > 1) {
            int mid = (int)cand.size() / 2;
            vector<int> left(cand.begin(), cand.begin() + mid);
            vector<int> right(cand.begin() + mid, cand.end());

            if (intersectNonEmpty(A_str, sizeA, neighA, left)) {
                cand.swap(left);
            } else {
                cand.swap(right);
            }
        }
        return cand[0];
    }

    int solveOne() {
        cin >> n;
        cache.clear();
        cache.reserve(8000);
        queryCount = 0;

        if (n <= 1) {
            cout << "! 1\n" << flush;
            return 1;
        }

        vector<char> inA(n, 0);
        inA[0] = 1;
        int sizeA = 1;
        string A_str(n, '0');
        A_str[0] = '1';

        while (true) {
            if (sizeA == n) {
                cout << "! 1\n" << flush;
                return 1;
            }

            int qA = ask(A_str);
            int neighA = sizeA + qA;

            vector<int> R;
            R.reserve(n - sizeA);
            string R_str(n, '0');
            for (int i = 0; i < n; i++) {
                if (!inA[i]) {
                    R.push_back(i);
                    R_str[i] = '1';
                }
            }

            int sizeR = n - sizeA;
            int qR = ask(R_str);
            int neighR = sizeR + qR;

            // N[A ∪ R] = N[V] = V, size = n
            int interAR = neighA + neighR - n;
            if (interAR == 0) {
                cout << "! 0\n" << flush;
                return 0;
            }

            int v = findOneCandidate(A_str, sizeA, neighA, R);
            inA[v] = 1;
            A_str[v] = '1';
            ++sizeA;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        InteractiveSolver solver;
        solver.solveOne();
    }
    return 0;
}