#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int n;
int questions_used = 0;
int max_questions = 53;

string ask(const vector<int>& s) {
    cout << "? " << s.size();
    for (int x : s) cout << " " << x;
    cout << endl;
    cout.flush();
    questions_used++;
    string ans;
    cin >> ans;
    return ans;
}

void guess(int g) {
    cout << "! " << g << endl;
    cout.flush();
    string resp;
    cin >> resp;
    if (resp == ":)") {
        exit(0);
    }
    // otherwise ":(" we continue
}

// Check if there exists a truthfulness sequence C (no two consecutive zeros)
// such that for each i, answer[i] == (C[i] ? correct[i] : !correct[i])
bool consistent(const vector<int>& answers, const vector<int>& correct) {
    int k = answers.size();
    // brute force all C of length k (2^k possibilities)
    for (int mask = 0; mask < (1 << k); ++mask) {
        vector<int> C(k);
        bool ok = true;
        for (int i = 0; i < k; ++i) {
            C[i] = (mask >> i) & 1;
        }
        // check no two consecutive zeros
        for (int i = 0; i + 1 < k; ++i) {
            if (C[i] == 0 && C[i + 1] == 0) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        // check answers match
        for (int i = 0; i < k; ++i) {
            int expected = C[i] ? correct[i] : (1 - correct[i]);
            if (expected != answers[i]) {
                ok = false;
                break;
            }
        }
        if (ok) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    int L = 1, R = n;

    while (R - L + 1 > 2) {
        // ensure we have enough questions left for at least 3 questions and 2 guesses
        if (questions_used + 3 > max_questions) break;

        int mid = (L + R) / 2;
        // left part [L, mid]
        vector<int> left;
        for (int i = L; i <= mid; ++i) left.push_back(i);
        // right part [mid+1, R]
        vector<int> right;
        for (int i = mid + 1; i <= R; ++i) right.push_back(i);

        string a1_str = ask(left);
        string a2_str = ask(left);
        int A1 = (a1_str == "YES") ? 1 : 0;
        int A2 = (a2_str == "YES") ? 1 : 0;

        if (A1 == A2) {
            if (A1 == 1) R = mid;
            else L = mid + 1;
        } else {
            // ask about right
            string a3_str = ask(right);
            int A3 = (a3_str == "YES") ? 1 : 0;
            vector<int> answers3 = {A1, A2, A3};

            // check for T = left (x in [L,mid])
            vector<int> correct_left = {1, 1, 0}; // for Q1(left), Q2(left), Q3(right)
            bool possible_left = consistent(answers3, correct_left);
            // check for T = right (x in [mid+1,R])
            vector<int> correct_right = {0, 0, 1};
            bool possible_right = consistent(answers3, correct_right);

            if (possible_left && !possible_right) {
                R = mid;
            } else if (possible_right && !possible_left) {
                L = mid + 1;
            } else {
                // ambiguous: need fourth question
                // ask about left again
                string a4_str = ask(left);
                int A4 = (a4_str == "YES") ? 1 : 0;
                vector<int> answers4 = {A1, A2, A3, A4};
                // correct sequences for four questions: Q1(left), Q2(left), Q3(right), Q4(left)
                vector<int> correct_left4 = {1, 1, 0, 1};
                vector<int> correct_right4 = {0, 0, 1, 0};
                bool possible_left4 = consistent(answers4, correct_left4);
                bool possible_right4 = consistent(answers4, correct_right4);
                if (possible_left4 && !possible_right4) {
                    R = mid;
                } else if (possible_right4 && !possible_left4) {
                    L = mid + 1;
                } else {
                    // should not happen, but fallback: choose left
                    R = mid;
                }
            }
        }
    }

    // Now we have at most 2 candidates left.
    // Guess each of them, we have two guesses.
    guess(L);
    if (L != R) {
        guess(R);
    }

    return 0;
}