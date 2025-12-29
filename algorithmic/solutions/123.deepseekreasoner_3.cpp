#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>

using namespace std;

int n;
int queriesUsed = 0;
int guessesUsed = 0;

// ask a membership query for set S
// returns true if answer is YES, false if NO
bool ask(const vector<int>& S) {
    queriesUsed++;
    cout << "? " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    string res;
    cin >> res;
    if (res == "YES") return true;
    else if (res == "NO") return false;
    else {
        // in case of unexpected response (should not happen)
        exit(1);
    }
}

// make a guess for x
void guess(int g) {
    guessesUsed++;
    cout << "! " << g << endl;
    cout.flush();
    string res;
    cin >> res;
    if (res == ":)") {
        // correct, exit immediately
        exit(0);
    } else if (res == ":(") {
        // incorrect, continue
        return;
    } else {
        exit(1);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    int l = 1, r = n;
    // previous answer not used explicitly

    while (r - l > 1) {
        int mid = (l + r) / 2;
        // construct set [l, mid]
        vector<int> S;
        for (int i = l; i <= mid; i++) {
            S.push_back(i);
        }

        // ask three times
        bool a1 = ask(S);
        bool a2 = ask(S);
        bool a3 = ask(S);

        // Determine truth based on patterns
        bool truth;
        if (a1 == a2) {
            truth = a1;
        } else if (a2 == a3) {
            truth = a2;
        } else if (a1 == a3) {
            // ambiguous pattern YNY or NYN
            // assume YES (i.e., x in [l, mid])
            truth = true;
        } else {
            // all three different? impossible with binary answers
            truth = a1; // fallback
        }

        if (truth) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }

    // Now we have at most two numbers
    guess(l);
    if (l != r) {
        guess(r);
    }

    // Should not reach here if guesses are correct
    return 0;
}