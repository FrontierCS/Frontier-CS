#include <iostream>
#include <vector>
#include <string>

using namespace std;

struct Rule {
    string left;
    string right;
    bool ret;
};

int main() {
    // A=B Program Generator
    // We don't read Tid, just output the A=B code.
    // However, the standard input might contain Tid, so we should read it to be safe/polite, 
    // although the problem says "Output your A=B program... The checker will use Tid...".
    // This implies we output the code regardless of input.
    // Standard competitive programming practice: just print the code.
    
    vector<Rule> rules;

    // Characters
    string chars = "abc";
    string T_inact = "ABC";
    string T_act = "DEF";
    string W_0 = "uvw"; // Wave with carry 0
    string W_1 = "xyz"; // Wave with carry 1
    string start = "0";
    string end_mark = "1";
    string wave_done = "W";
    string setup_S = "S";
    string setup_M = "M";

    // 1. Success Termination: Active Block + WaveDone -> Return 1
    // D W = (return)1
    for (char act : T_act) {
        rules.push_back({string(1, act) + wave_done, "1", true});
    }

    // 2. Failure Termination: Start + EndMark -> Return 0
    // 0 1 = (return)0
    rules.push_back({start + end_mark, "0", true});

    // 3. Wave Start: Start + char -> Start + Wave(char, 1)
    // 0 a = 0 x
    for (int i = 0; i < 3; ++i) {
        rules.push_back({start + string(1, chars[i]), start + string(1, W_1[i]), false});
    }

    // 4. Interaction Rules (Wave x Block)
    // Wave moves Right, Block is stationary relative to T structure.
    for (int w_idx = 0; w_idx < 3; ++w_idx) { // for each wave char (carrying a, b, c)
        for (int b_idx = 0; b_idx < 3; ++b_idx) { // for each block char type (A, B, C)
            bool match = (w_idx == b_idx);
            
            // Carry 0 (u,v,w) x Inactive (A,B,C)
            // In=0, Old=0. New = 0&&match = 0 (Inactive). Out = 0.
            // u A = A u
            rules.push_back({
                string(1, W_0[w_idx]) + string(1, T_inact[b_idx]),
                string(1, T_inact[b_idx]) + string(1, W_0[w_idx]),
                false
            });

            // Carry 0 (u,v,w) x Active (D,E,F)
            // In=0, Old=1. New = 0&&match = 0 (Inactive). Out = 1.
            // u D = A x
            rules.push_back({
                string(1, W_0[w_idx]) + string(1, T_act[b_idx]),
                string(1, T_inact[b_idx]) + string(1, W_1[w_idx]),
                false
            });

            // Carry 1 (x,y,z) x Inactive (A,B,C)
            // In=1, Old=0. New = 1&&match. Out = 0.
            if (match) {
                // x A = D u
                rules.push_back({
                    string(1, W_1[w_idx]) + string(1, T_inact[b_idx]),
                    string(1, T_act[b_idx]) + string(1, W_0[w_idx]),
                    false
                });
            } else {
                // x B = B u
                rules.push_back({
                    string(1, W_1[w_idx]) + string(1, T_inact[b_idx]),
                    string(1, T_inact[b_idx]) + string(1, W_0[w_idx]),
                    false
                });
            }

            // Carry 1 (x,y,z) x Active (D,E,F)
            // In=1, Old=1. New = 1&&match. Out = 1.
            if (match) {
                // x D = D x
                rules.push_back({
                    string(1, W_1[w_idx]) + string(1, T_act[b_idx]),
                    string(1, T_act[b_idx]) + string(1, W_1[w_idx]),
                    false
                });
            } else {
                // x E = B x
                rules.push_back({
                    string(1, W_1[w_idx]) + string(1, T_act[b_idx]),
                    string(1, T_inact[b_idx]) + string(1, W_1[w_idx]),
                    false
                });
            }
        }
    }

    // 5. Wave Exit: Wave + (s-char or EndMark) -> WaveDone + ...
    // u a = W a
    string s_context = chars + end_mark;
    for (int w_idx = 0; w_idx < 3; ++w_idx) {
        for (char next : s_context) {
            // Carry 0
            rules.push_back({
                string(1, W_0[w_idx]) + string(1, next),
                wave_done + string(1, next),
                false
            });
            // Carry 1
            rules.push_back({
                string(1, W_1[w_idx]) + string(1, next),
                wave_done + string(1, next),
                false
            });
        }
    }

    // 6. Cleanup: WaveDone + (s-char or EndMark) -> (s-char or EndMark)
    // W a = a
    for (char next : s_context) {
        rules.push_back({
            wave_done + string(1, next),
            string(1, next),
            false
        });
    }

    // 7. Crossing: T-Block (Active/Inactive) + s-char -> s-char + T-Block
    // A a = a A
    string all_T = T_inact + T_act;
    for (char t : all_T) {
        for (char s : chars) {
            rules.push_back({
                string(1, t) + string(1, s),
                string(1, s) + string(1, t),
                false
            });
        }
    }

    // 8. Setup
    // S a = A S
    for (int i = 0; i < 3; ++i) {
        rules.push_back({
            setup_S + string(1, chars[i]),
            string(1, T_inact[i]) + setup_S,
            false
        });
    }

    // S = M 1
    rules.push_back({setup_S, setup_M + end_mark, false});

    // M crossing s-char: a M = M a
    for (char s : chars) {
        rules.push_back({
            string(1, s) + setup_M,
            setup_M + string(1, s),
            false
        });
    }
    
    // M crossing 1: 1 M = M 1
    rules.push_back({end_mark + setup_M, setup_M + end_mark, false});

    // M crossing T (Inactive): A M = M A
    for (char t : T_inact) {
        rules.push_back({
            string(1, t) + setup_M,
            setup_M + string(1, t),
            false
        });
    }

    // M = 0
    rules.push_back({setup_M, start, false});

    // Output rules
    for (const auto& r : rules) {
        cout << r.left << "=" << (r.ret ? "(return)" : "") << r.right << "\n";
    }

    return 0;
}