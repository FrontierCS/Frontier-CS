#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}


// Legacy base ratio, retained only to decide and preserve the lower band.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

// checker.cpp
// testlib special judge for the Number Loop construction problem.
// Counts the single loops satisfying every clue of the contestant's puzzle,
// capped at six, with an exact plug DP over the grid points: the count does
// not depend on how weakly the clues constrain the board.
// Requires testlib.h in include path.

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

const int N = 12;
const vector<string> M = {
    "?   ?   ??? ",
    "?? ??  ?   ?",
    "? ? ?  ?   ?",
    "? ? ?  ???? ",
    "? ? ?  ?    ",
    "?   ?  ?    ",
    "            ",
    "?  ?   ?????",
    "? ?      ?  ",
    "??   ? ? ?  ",
    "? ?  ? ? ?  ",
    "?  ? ??? ?  "
};

string valid_char;
vector<string> grid;

int clue_cell_count(){
    int total = 0;
    for(const string &row : M) {
        for(char c : row) {
            if(c == '?') total++;
        }
    }
    return total;
}

int count_ones(){
    int total = 0;
    for(const string &row : grid) {
        for(char c : row) {
            if(c == '1') total++;
        }
    }
    return total;
}

double score_percent(int solution_count){
    if(solution_count <= 0) return 0.0;

    const double u = (double)count_ones() / (double)clue_cell_count();
    if(solution_count >= 6) return 1.0 + 9.0 * u;
    if(solution_count == 5) return 10.0 + 10.0 * u;
    if(solution_count == 4) return 20.0 + 10.0 * u;
    if(solution_count == 3) return 30.0 + 10.0 * u;
    if(solution_count == 2) return 40.0 + 10.0 * u;
    return 50.0 + 50.0 * u;
}

void myAssert(bool cond, const string &msg){
    if(!cond) {
        // In SPJ we usually call quitf for WA, but here follow original: print to stderr and exit
        quitf(_pe, "Assertion failed: %s", msg.c_str());
    }
}

string clean_line(string line){
    const string allowed = " 0123";
    while(!line.empty() && allowed.find(line.front())==string::npos) line.erase(line.begin());
    while(!line.empty() && allowed.find(line.back())==string::npos) line.pop_back();
    return line;
}

vector<string> readSol(InStream &in){
    vector<string> res;
    for(int i=0;i<N;i++){
        string line = in.readLine();
        line = clean_line(line);
        myAssert((int)line.size()==12, "The size of the result should be 12 * 12");
        for(int j=0;j<12;j++){
            char c = line[j];
            myAssert(valid_char.find(c)!=string::npos, string("Invalid char ") + c);
            if(c != ' ')
                myAssert(M[i][j] == '?', "Position (" + to_string(i) + "," + to_string(j) + ") should be empty");
            else
                myAssert(M[i][j] == ' ', "Position (" + to_string(i) + "," + to_string(j) + ") should be non-empty");
        }
        res.push_back(line);
    }
    return res;
}

// Loop counting: plug (profile) DP over the (N+1) x (N+1) grid points in
// row-major order. Point (i, j) decides the edge to its right, H[i][j], and
// the edge below it, V[i][j]. Before point (i, j) the profile has N+2 slots:
//   slot k < j : V[i][k], below an already processed point of row i
//   slot j     : H[i][j-1], entering (i, j) from the left
//   slot k > j : V[i-1][k-1], entering (i, k-1) from above
// A slot is 0 (no edge) or an end of an open path, 1 for its left end and 2
// for its right end, so the slots form a balanced bracket sequence. Cell
// (r, c) is checked when point (r+1, c) decides its bottom edge; its top edge
// H[r][c] has left the profile by then, so it is kept as one bit per column.
// One more bit records that the loop is closed, after which no edge may be
// added. Every edge set is reached by exactly one path through the DP.

const int P = N + 1;                 // grid points per side
const int SLOTS = P + 1;
const int TOP_SHIFT = 2 * SLOTS;     // top-edge bits follow the slots
const uint64_t PLUG_MASK = (1ULL << TOP_SHIFT) - 1;
const uint64_t CLOSED = 1ULL << (TOP_SHIFT + N);

int slot_of(uint64_t s, int k){ return (int)((s >> (2 * k)) & 3); }

uint64_t with_slot(uint64_t s, int k, int v){
    return (s & ~(3ULL << (2 * k))) | ((uint64_t)v << (2 * k));
}

// Slot holding the other end of the path that ends in slot k.
int matching_slot(uint64_t s, int k){
    const int own = slot_of(s, k);
    const int dir = own == 1 ? 1 : -1;
    int depth = 0;
    for(int t = k; t >= 0 && t < SLOTS; t += dir){
        const int v = slot_of(s, t);
        if(v == 0) continue;
        depth += v == own ? 1 : -1;
        if(depth == 0) return t;
    }
    quitf(_fail, "Unbalanced plug profile");
    return -1;
}

// Clue digit of cell (r, c), or -1 for a blank or out-of-grid cell.
int clue_at(int r, int c){
    if(r < 0 || r >= N || c < 0 || c >= N || grid[r][c] == ' ') return -1;
    return grid[r][c] - '0';
}

// Map from DP state to its number of ways (at most LIMIT), by open
// addressing. A hard board reaches about 10^6 states per step, so each entry
// keeps its count in the high bits of its state word to halve the memory.
struct StateMap {
    static constexpr int WAYS_SHIFT = 56;          // states use the bits below
    static constexpr uint64_t STATE_BITS = (1ULL << WAYS_SHIFT) - 1;
    static constexpr uint64_t EMPTY = ~0ULL;       // never a valid entry
    int bits;
    vector<uint64_t> table;
    vector<uint32_t> used;                         // occupied entries

    StateMap(){ bits = 0; rehash(16); }

    size_t find(uint64_t state) const {
        const size_t mask = table.size() - 1;
        size_t h = (size_t)((state * 0x9E3779B97F4A7C15ULL) >> (64 - bits));
        while(table[h] != EMPTY && (table[h] & STATE_BITS) != state) h = (h + 1) & mask;
        return h;
    }

    void rehash(int new_bits){
        vector<uint64_t> old_table(1ULL << new_bits, EMPTY);
        vector<uint32_t> old_used;
        table.swap(old_table);
        used.swap(old_used);
        bits = new_bits;
        for(uint32_t h : old_used){
            const size_t g = find(state(old_table[h]));
            table[g] = old_table[h];
            used.push_back((uint32_t)g);
        }
    }

    static uint64_t state(uint64_t entry){ return entry & STATE_BITS; }
    static int ways(uint64_t entry){ return (int)(entry >> WAYS_SHIFT); }

    // ways[s] += w, capped at limit (below 256, to fit in the entry).
    void add(uint64_t s, int w, int limit){
        if(2 * (used.size() + 1) > table.size()) rehash(bits + 1);
        const size_t h = find(s);
        int now = w;
        if(table[h] == EMPTY) used.push_back((uint32_t)h);
        else now += ways(table[h]);
        table[h] = s | ((uint64_t)min(limit, now) << WAYS_SHIFT);
    }

    int get(uint64_t s) const {
        const uint64_t entry = table[find(s)];
        return entry == EMPTY ? 0 : ways(entry);
    }

    void clear(){
        for(uint32_t h : used) table[h] = EMPTY;
        used.clear();
    }
};

// Number of single loops that satisfy every clue, capped at limit.
int count_solutions(int limit){
    StateMap cur, nxt;
    cur.add(0, 1, limit);
    for(int i = 0; i < P; i++){
        for(int j = 0; j < P; j++){
            // Clues of the cells whose edges point (i, j) completes or starts.
            const int d_done = clue_at(i - 1, j);   // all four edges known
            const int d_left = clue_at(i, j - 1);   // top, left and right known
            const int d_here = clue_at(i, j);       // top and left known
            nxt.clear();
            for(uint32_t h : cur.used){
                const uint64_t s = StateMap::state(cur.table[h]);
                const int ways = StateMap::ways(cur.table[h]);
                const int L = slot_of(s, j), U = slot_of(s, j + 1);
                for(int right = 0; right <= 1; right++){
                    for(int down = 0; down <= 1; down++){
                        if(right && j == N) continue;
                        if(down && i == N) continue;
                        const int deg = (L != 0) + (U != 0) + right + down;
                        if(deg != 0 && deg != 2) continue;
                        if(deg != 0 && (s & CLOSED)) continue;

                        if(d_done >= 0){
                            const int have = (int)((s >> (TOP_SHIFT + j)) & 1) + (U != 0)
                                           + (slot_of(s, j + 2) != 0) + right;
                            if(have != d_done) continue;
                        }
                        if(d_left >= 0){
                            const int have = (L != 0) + (slot_of(s, j - 1) != 0) + down;
                            if(have > d_left || have + 1 < d_left) continue;
                        }
                        if(d_here >= 0 && (right + down > d_here || right + down + 2 < d_here)) continue;

                        uint64_t t = with_slot(with_slot(s, j, 0), j + 1, 0);
                        if(L != 0 && U != 0){
                            if(L == 1 && U == 1){
                                t = with_slot(t, matching_slot(s, j + 1), 1);
                            } else if(L == 2 && U == 2){
                                t = with_slot(t, matching_slot(s, j), 2);
                            } else if(L == 1 && U == 2){
                                // Joining the two ends of one path closes a
                                // loop, which must then be the only one.
                                if(t & PLUG_MASK) continue;
                                t |= CLOSED;
                            }
                        } else if(L != 0 || U != 0){
                            t = with_slot(t, down ? j : j + 1, L | U);
                        } else if(deg != 0){
                            t = with_slot(with_slot(t, j, 1), j + 1, 2);
                        }

                        if(j < N){
                            t &= ~(1ULL << (TOP_SHIFT + j));
                            if(right && d_here >= 0) t |= 1ULL << (TOP_SHIFT + j);
                        }
                        nxt.add(t, ways, limit);
                    }
                }
            }
            swap(cur, nxt);
        }
        // Next row: every slot moves one to the right and slot 0 opens empty.
        nxt.clear();
        for(uint32_t h : cur.used){
            const uint64_t s = StateMap::state(cur.table[h]);
            nxt.add((s & ~PLUG_MASK) | ((s << 2) & PLUG_MASK), StateMap::ways(cur.table[h]), limit);
        }
        swap(cur, nxt);
    }
    return cur.get(CLOSED);
}

int main(int argc, char **argv){
    registerTestlibCmd(argc, argv);

    // read type from input file (inf)
    int w = inf.readInt();
    if(w == 0) valid_char = " 0123";
    else valid_char = " 123";

    // read contestant output (ouf) as grid grid
    grid = readSol(ouf);

    // Count solutions up to the cap that fixes the score bucket.
    const int LIMIT = 6;
    const int cnt = count_solutions(LIMIT);

    if(cnt == 0){
        quitp(0.0, "There is no valid solution");
    }

    const int ones = count_ones();
    const int clues = clue_cell_count();
    double score = 100.0 * penalized(score_percent(cnt) / 100.0);
    if (cnt == 1) score = natural_log_score(score, clues - ones, 0.8L * clues, true);
    const string count_label = cnt >= 6 ? "six or more" : to_string(cnt);
    quitp(
        score / 100.0,
        "Ratio: %.12f RatioUnbounded: %.12f Score: %.6f, solutions: %s, ones: %d/%d",
        score / 100.0,
        score / 100.0,
        score,
        count_label.c_str(),
        ones,
        clues
    );
    return 0;
}
