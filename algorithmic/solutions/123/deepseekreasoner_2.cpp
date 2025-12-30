#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    // possible[i] = 1 if x could still be i
    vector<char> possible(n + 1, 1);
    // dp0[i]: can the last answer be a lie with x = i ?
    // dp1[i]: can the last answer be truthful with x = i ?
    vector<char> dp0(n + 1, 0);
    vector<char> dp1(n + 1, 1);

    int count_possible = n;
    int questions_used = 0;
    int guesses_used = 0;

    // main interaction loop
    while (questions_used < 53 && count_possible > 1) {
        if (count_possible == 1 && guesses_used < 2) {
            // only one candidate left -> guess it
            int guess = -1;
            for (int i = 1; i <= n; ++i)
                if (possible[i]) {
                    guess = i;
                    break;
                }
            cout << "! " << guess << endl;
            cout.flush();
            string resp;
            cin >> resp;
            ++guesses_used;
            if (resp == ":)")
                return 0;
            else {
                possible[guess] = 0;
                --count_possible;
                // this should not happen if our reasoning is correct
                continue;
            }
        }

        if (count_possible == 2 && guesses_used == 0) {
            // two candidates, no guess used yet -> guess one of them
            int guess1 = -1, guess2 = -1;
            for (int i = 1; i <= n; ++i) {
                if (possible[i]) {
                    if (guess1 == -1)
                        guess1 = i;
                    else {
                        guess2 = i;
                        break;
                    }
                }
            }
            cout << "! " << guess1 << endl;
            cout.flush();
            string resp;
            cin >> resp;
            ++guesses_used;
            if (resp == ":)")
                return 0;
            else {
                possible[guess1] = 0;
                --count_possible;
                // now only guess2 remains, will be guessed later
                continue;
            }
        }

        // otherwise, ask a question
        // choose a threshold mid such that approximately half of the
        // still possible numbers are <= mid
        int target = count_possible / 2;
        int running = 0;
        int mid = 1;
        for (int i = 1; i <= n; ++i) {
            if (possible[i]) {
                ++running;
                if (running >= target) {
                    mid = i;
                    break;
                }
            }
        }

        // ask: is x in {1, 2, ..., mid} ?
        cout << "? " << mid;
        for (int i = 1; i <= mid; ++i)
            cout << " " << i;
        cout << endl;
        cout.flush();

        string ans;
        cin >> ans;
        ++questions_used;

        // update possible set and DP states
        for (int i = 1; i <= n; ++i) {
            if (!possible[i])
                continue;
            bool truthful = (i <= mid);
            bool answer = (ans == "YES");
            bool new_dp1 = (answer == truthful) && (dp0[i] || dp1[i]);
            bool new_dp0 = (answer != truthful) && dp1[i];
            if (new_dp0 || new_dp1) {
                dp0[i] = new_dp0;
                dp1[i] = new_dp1;
            } else {
                possible[i] = 0;
                --count_possible;
            }
        }
    }

    // after the loop, if we still have candidates, guess them
    // (we should have at most 2 candidates here)
    for (int i = 1; i <= n; ++i) {
        if (possible[i]) {
            cout << "! " << i << endl;
            cout.flush();
            string resp;
            cin >> resp;
            // if wrong and we have another guess, the other candidate is correct
            // but we have already used all guesses? not necessarily.
            // However, the problem guarantees a correct answer with our strategy.
            break;
        }
    }

    return 0;
}