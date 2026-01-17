#include <bits/stdc++.h>
using namespace std;

long long sum_tz(long long rr) {
    if (rr <= 0) return 0;
    long long res = 0;
    for (long long p = 2; p <= rr; p <<= 1) {
        res += rr / p;
    }
    return res;
}

int get_l(long long rr) {
    if (rr == 0) return 0;
    int res = 0;
    long long t = rr;
    while (t) {
        res++;
        t >>= 1;
    }
    return res;
}

long long total_steps(long long rr) {
    if (rr == 0) return 1LL;
    int ll = get_l(rr);
    long long S_decr = sum_tz(rr);
    long long sum_d = 4 * S_decr + 2 * rr;
    long long S_ch = sum_tz(rr - 1);
    long long num_nz_ch = max(0LL, rr - 1);
    long long sum_ch_nz = 2 * S_ch + 4 * num_nz_ch;
    long long ch_zero = 3LL * ll;
    return (long long)ll + sum_d + sum_ch_nz + ch_zero + 1;
}

void generate_small(vector<string>& prog, int start, long long d) {
    long long m = (d - 1) / 2;
    if (m == 0) return;
    if (m == 1) {
        int s = start;
        prog.push_back("POP 1 GOTO " + to_string(s + 1) + " PUSH 1 GOTO " + to_string(s + 1));
        prog.push_back("POP 1 GOTO " + to_string(s + 2) + " PUSH 2 GOTO " + to_string(s + 2));
        prog.push_back("HALT PUSH 1 GOTO " + to_string(s));
    } else {
        int s = start;
        prog.push_back("POP 3 GOTO " + to_string(s) + " PUSH 1 GOTO " + to_string(s + 1));
        prog.push_back("HALT PUSH 1 GOTO " + to_string(s + 2));
        for (long long loc_i = 3; loc_i <= m; loc_i++) {
            int global_i = s + loc_i - 1;
            int nextg = s + loc_i;
            prog.push_back("POP 3 GOTO " + to_string(s) + " PUSH 1 GOTO " + to_string(nextg));
        }
        for (long long loc_j = 1; loc_j <= m; loc_j++) {
            int global_j = s + m + loc_j - 1;
            int nextg = (loc_j < m) ? (s + m + loc_j) : (s + 1);
            prog.push_back("POP 1 GOTO " + to_string(nextg) + " PUSH 99 GOTO " + to_string(s));
        }
    }
}

int main() {
    long long k;
    cin >> k;
    auto sumt = sum_tz;
    auto getl = get_l;
    auto tot = total_steps;
    long long lo = 0, hi = k * 2LL;
    while (lo < hi) {
        long long mid = lo + (hi - lo + 1) / 2;
        long long ts = tot(mid);
        if (ts <= k && ts % 2 == 1) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    long long r = lo;
    long long ts = tot(r);
    while (r >= 0 && (ts > k || ts % 2 != 1)) {
        r--;
        ts = tot(r);
    }
    long long d = k - ts + 1;
    vector<string> prog;
    if (r == 0) {
        if (d == 1) {
            prog.push_back("HALT PUSH 1 GOTO 1");
        } else {
            generate_small(prog, 1, d);
        }
    } else {
        int lll = getl(r);
        int curr = 1;
        for (int i = 1; i <= lll; i++) {
            int pos = lll - i;
            int val = ((r & (1LL << pos)) != 0) ? 2 : 1;
            string ln = "POP 3 GOTO 1 PUSH " + to_string(val) + " GOTO " + to_string(curr + 1);
            prog.push_back(ln);
            curr++;
        }
        int decr_s = curr;
        for (int b = 0; b < lll; b++) {
            int B = curr;
            int B1 = B + 1;
            int B_popold = B + 2;
            int B_push2 = B + 3;
            int B_push1 = B + 4;
            int nextb = (b < lll - 1) ? (B + 5) : decr_s;
            prog.push_back("POP 2 GOTO " + to_string(B_push1) + " PUSH 1 GOTO " + to_string(B1));
            prog.push_back("POP 1 GOTO " + to_string(B_popold) + " PUSH 99 GOTO 1");
            prog.push_back("POP 1 GOTO " + to_string(B_push2) + " PUSH 99 GOTO 1");
            prog.push_back("PUSH 2 GOTO " + to_string(nextb));
            prog.push_back("PUSH 1 GOTO " + to_string(decr_s));
            curr += 5;
        }
        int check_s = curr;
        int pop1_s_temp = -1; // to set later
        for (int b = 0; b < lll; b++) {
            int C = curr;
            int C1 = C + 1;
            int C_popold = C + 2;
            int C_push2 = C + 3;
            int C_push1 = C + 4;
            int nextc = (b < lll - 1) ? (C + 5) : 0; // placeholder
            prog.push_back("POP 1 GOTO " + to_string(C_push1) + " PUSH 1 GOTO " + to_string(C1));
            prog.push_back("POP 1 GOTO " + to_string(C_popold) + " PUSH 99 GOTO 1");
            prog.push_back("POP 2 GOTO " + to_string(C_push2) + " PUSH 99 GOTO 1");
            prog.push_back("PUSH 2 GOTO " + to_string(decr_s));
            string placeholder = "PUSH 1 GOTO " + to_string(nextc); // will overwrite if last
            prog.push_back(placeholder);
            curr += 5;
        }
        // now pop1
        int pop1_s = curr;
        bool use_sm = (d > 1);
        int final_goto_temp = use_sm ? (pop1_s + lll) : (pop1_s + lll);
        for (int i = 0; i < lll; i++) {
            int P = curr;
            int gnext_p = (i < lll - 1) ? (P + 1) : final_goto_temp;
            prog.push_back("POP 1 GOTO " + to_string(gnext_p) + " PUSH 99 GOTO 1");
            curr++;
        }
        int after_p = curr;
        // set the last check push1
        int last_C = check_s + 5 * (lll - 1);
        int last_C_push1 = last_C + 4;
        prog[last_C_push1 - 1] = "PUSH 1 GOTO " + to_string(pop1_s);
        if (!use_sm) {
            prog.push_back("HALT PUSH 1 GOTO " + to_string(after_p));
            curr++;
        } else {
            generate_small(prog, after_p, d);
            curr += ( ( (d-1)/2 ==1 ) ? 3 : 2 * ((d-1)/2) );
        }
    }
    int n = prog.size();
    cout << n << endl;
    for (string ln : prog) {
        cout << ln << endl;
    }
    return 0;
}