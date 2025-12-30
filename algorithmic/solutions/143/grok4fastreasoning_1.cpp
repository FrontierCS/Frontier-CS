#include <bits/stdc++.h>
using namespace std;

string read_token() {
    string t;
    cin >> t;
    if (t == "-1") {
        exit(0);
    }
    return t;
}

int read_int() {
    return stoi(read_token());
}

double read_double() {
    return stod(read_token());
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int dummy_g = read_int(); // G

    while (true) {
        string cmd = read_token();
        if (cmd == "SCORE") {
            read_double();
            break;
        }
        // STATE
        int hand = read_int();
        int r = read_int();
        int a = read_int();
        int b = read_int();
        int P = read_int();
        int k = read_int();

        // ALICE
        read_token(); // ALICE
        int s1 = read_int(), v1 = read_int(), s2 = read_int(), v2 = read_int();
        vector<pair<int, int>> my_hole = {{s1, v1}, {s2, v2}};

        // BOARD
        read_token(); // BOARD
        vector<pair<int, int>> board(k);
        for (int i = 0; i < k; i++) {
            int ss = read_int(), vv = read_int();
            board[i] = {ss, vv};
        }

        // RATE
        int tt = 75;
        cout << "RATE " << tt << endl;
        fflush(stdout);

        read_token(); // RATES
        double w = read_double();
        double d = read_double();
        double e = w + 0.5 * d;

        // decide
        string act_str;
        int x = 0;
        if (r == 4 || e < 0.55) {
            act_str = "CHECK";
        } else {
            x = min(a, P);
            if (x < 1) x = 1;
            act_str = "RAISE " + to_string(x);
        }
        cout << "ACTION " << act_str << endl;
        fflush(stdout);

        // response
        read_token(); // OPP
        string opp_act = read_token();
        bool hand_ends = false;
        if (act_str.find("CHECK") != string::npos) {
            // OPP CHECK
            if (r == 4) {
                hand_ends = true;
            }
        } else {
            if (opp_act == "FOLD") {
                hand_ends = true;
            } else {
                // CALL x
                int cx = read_int();
                if (r == 4) {
                    hand_ends = true;
                }
            }
        }
        if (hand_ends) {
            read_token(); // RESULT
            read_int(); // delta
        }
    }
    return 0;
}