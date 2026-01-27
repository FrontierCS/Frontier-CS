#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 1);

    auto ask = [&](const vector<int>& S) -> string {
        cout << "? " << S.size();
        for (int v : S) cout << " " << v;
        cout << "\n" << flush;
        string resp;
        if (!(cin >> resp)) exit(0);
        return resp;
    };

    auto guess = [&](int g) {
        cout << "! " << g << "\n" << flush;
        string resp;
        if (!(cin >> resp)) exit(0);
        if (resp == ":)") exit(0);
        // If wrong, we could continue, but our strategy shouldn't reach here.
        // Still, handle gracefully by exiting.
        exit(0);
    };

    while (true) {
        if (cand.size() == 1) {
            guess(cand[0]);
        }
        int m = (int)cand.size();
        int k = m / 2; // first half size (>=1 since m>=2)
        vector<int> A(cand.begin(), cand.begin() + k);
        vector<int> B(cand.begin() + k, cand.end());

        string r1 = ask(A);
        string r2 = ask(B);

        // Decision rule:
        // If (YES, NO) -> x in A, else x in B
        if (r1 == "YES" && r2 == "NO") {
            cand = A;
        } else {
            cand = B;
        }
    }

    return 0;
}