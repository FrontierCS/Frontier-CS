#include <bits/stdc++.h>
using namespace std;

// Minimal JSON parser sufficient for the given problem structure

struct JValue {
    enum Type { OBJECT, ARRAY, STRING, NUMBER, BOOL, NIL } type = NIL;
    unordered_map<string, JValue> obj;
    vector<JValue> arr;
    string str;
    long long num = 0;
    bool boolean = false;
};

struct JSONParser {
    const string *s;
    size_t i = 0;

    JSONParser(const string &input) { s = &input; i = 0; }

    void skip_ws() {
        while (i < s->size() && isspace((*s)[i])) i++;
    }

    bool match(const string &t) {
        skip_ws();
        if (s->substr(i, t.size()) == t) {
            i += t.size();
            return true;
        }
        return false;
    }

    char peek() {
        skip_ws();
        if (i < s->size()) return (*s)[i];
        return '\0';
    }

    char get() {
        if (i < s->size()) return (*s)[i++];
        return '\0';
    }

    string parse_string() {
        skip_ws();
        string out;
        if (get() != '"') return out;
        while (i < s->size()) {
            char c = get();
            if (c == '"') break;
            if (c == '\\') {
                if (i >= s->size()) break;
                char e = get();
                switch (e) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    default: out.push_back(e); break;
                }
            } else {
                out.push_back(c);
            }
        }
        return out;
    }

    long long parse_number() {
        skip_ws();
        long long sign = 1;
        if (i < s->size() && (*s)[i] == '-') { sign = -1; i++; }
        long long val = 0;
        while (i < s->size() && isdigit((*s)[i])) {
            val = val * 10 + ((*s)[i] - '0');
            i++;
        }
        return sign * val;
    }

    JValue parse_value() {
        skip_ws();
        JValue v;
        char c = peek();
        if (c == '{') {
            v.type = JValue::OBJECT;
            get(); // {
            skip_ws();
            if (peek() == '}') { get(); return v; }
            while (true) {
                string key = parse_string();
                skip_ws();
                if (get() != ':') { /* error */ }
                JValue val = parse_value();
                v.obj.emplace(key, std::move(val));
                skip_ws();
                char ch = get();
                if (ch == '}') break;
                if (ch != ',') { /* error */ break; }
            }
            return v;
        } else if (c == '[') {
            v.type = JValue::ARRAY;
            get(); // [
            skip_ws();
            if (peek() == ']') { get(); return v; }
            while (true) {
                JValue val = parse_value();
                v.arr.push_back(std::move(val));
                skip_ws();
                char ch = get();
                if (ch == ']') break;
                if (ch != ',') { /* error */ break; }
            }
            return v;
        } else if (c == '"') {
            v.type = JValue::STRING;
            v.str = parse_string();
            return v;
        } else if (c == '-' || isdigit(c)) {
            v.type = JValue::NUMBER;
            v.num = parse_number();
            return v;
        } else if (s->substr(i, 4) == "true") {
            v.type = JValue::BOOL;
            v.boolean = true;
            i += 4;
            return v;
        } else if (s->substr(i, 5) == "false") {
            v.type = JValue::BOOL;
            v.boolean = false;
            i += 5;
            return v;
        } else if (s->substr(i, 4) == "null") {
            v.type = JValue::NIL;
            i += 4;
            return v;
        }
        // Fallback
        v.type = JValue::NIL;
        return v;
    }
};

// Data structures for packing

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
    int remain;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

struct Node {
    int x;
    int y;
    int width;
};

struct Skyline {
    int W, H;
    vector<Node> nodes;

    Skyline(int W_, int H_) : W(W_), H(H_) {
        nodes.push_back({0, 0, W});
    }

    void mergeNeighbors() {
        vector<Node> merged;
        for (auto &n : nodes) {
            if (!merged.empty() && merged.back().y == n.y) {
                merged.back().width += n.width;
            } else {
                merged.push_back(n);
            }
        }
        nodes.swap(merged);
    }

    void splitAt(int xpos) {
        if (xpos <= 0 || xpos >= W) {
            // May still need to ensure exact boundary splitting if equals some boundary
            return;
        }
        // If already at node boundary, nothing to do
        for (size_t idx = 0; idx < nodes.size(); ++idx) {
            if (nodes[idx].x == xpos) return;
            int x0 = nodes[idx].x;
            int x1 = x0 + nodes[idx].width;
            if (xpos > x0 && xpos < x1) {
                // split
                Node left = nodes[idx];
                Node right;
                left.width = xpos - x0;
                right.x = xpos;
                right.y = nodes[idx].y;
                right.width = x1 - xpos;
                nodes[idx] = left;
                nodes.insert(nodes.begin() + idx + 1, right);
                return;
            }
        }
    }

    // Find best position for rectangle (rw, rh)
    // Returns pair<bool, tuple<x, y>>
    // Selection: minimal y; tie minimal x
    bool find_position(int rw, int rh, int &best_x, int &best_y) {
        int bestY = INT_MAX;
        int bestX = 0;
        for (size_t i = 0; i < nodes.size(); ++i) {
            int x0 = nodes[i].x;
            int acc = 0;
            int maxH = 0;
            size_t j = i;
            while (j < nodes.size() && acc < rw) {
                maxH = max(maxH, nodes[j].y);
                acc += nodes[j].width;
                ++j;
            }
            if (acc < rw) break; // cannot fit starting here
            if (maxH + rh <= H) {
                if (maxH < bestY || (maxH == bestY && x0 < bestX)) {
                    bestY = maxH;
                    bestX = x0;
                }
            }
        }
        if (bestY == INT_MAX) return false;
        best_x = bestX;
        best_y = bestY;
        return true;
    }

    void place(int x, int y, int rw, int rh) {
        // Prepare boundaries
        splitAt(x);
        splitAt(x + rw);
        // Replace nodes in [x, x+rw) with single node at height y+rh
        // First find index where node.x == x
        size_t i = 0;
        while (i < nodes.size() && nodes[i].x != x) ++i;
        // Remove nodes while within covered range
        size_t start = i;
        int coveredEnd = x + rw;
        while (i < nodes.size() && nodes[i].x < coveredEnd) {
            i++;
        }
        // Erase [start, i)
        nodes.erase(nodes.begin() + start, nodes.begin() + i);
        // Insert new node
        nodes.insert(nodes.begin() + start, Node{x, y + rh, rw});
        // Normalize x positions and merge
        // Recompute x of nodes after start based on widths
        if (!nodes.empty()) {
            nodes[0].x = 0;
            for (size_t k = 1; k < nodes.size(); ++k) {
                nodes[k].x = nodes[k - 1].x + nodes[k - 1].width;
            }
        }
        mergeNeighbors();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input
    string input, line;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    JSONParser parser(input);
    JValue root = parser.parse_value();

    // Extract bin
    auto &bin = root.obj["bin"];
    int W = (int)bin.obj["W"].num;
    int H = (int)bin.obj["H"].num;
    bool allow_rotate = bin.obj["allow_rotate"].boolean;

    // Extract items
    vector<ItemType> items;
    for (auto &jitem : root.obj["items"].arr) {
        ItemType t;
        t.id = jitem.obj.at("type").str;
        t.w = (int)jitem.obj.at("w").num;
        t.h = (int)jitem.obj.at("h").num;
        t.v = jitem.obj.at("v").num;
        t.limit = (int)jitem.obj.at("limit").num;
        t.remain = t.limit;
        items.push_back(t);
    }

    Skyline sky(W, H);
    vector<Placement> placements;

    // Heuristic: iterative, at each step choose available item/rotation that fits with highest value density
    auto better_density = [](long long v1, int a1, long long v2, int a2) -> bool {
        // return true if v1/a1 > v2/a2
        return (__int128)v1 * a2 > (__int128)v2 * a1;
    };

    while (true) {
        bool anyFit = false;
        int best_t = -1;
        int best_rot = 0;
        int best_x = 0, best_y = 0;
        long long best_v = 0;
        int best_area = 1;

        for (int t = 0; t < (int)items.size(); ++t) {
            if (items[t].remain <= 0) continue;

            for (int rot = 0; rot <= 1; ++rot) {
                if (rot == 1 && !allow_rotate) continue;
                int rw = items[t].w;
                int rh = items[t].h;
                if (rot == 1) { rw = items[t].h; rh = items[t].w; }
                if (rw > W || rh > H) continue;

                int x, y;
                if (sky.find_position(rw, rh, x, y)) {
                    anyFit = true;
                    int area = rw * rh;
                    if (best_t == -1 ||
                        better_density(items[t].v, area, best_v, best_area) ||
                        (!better_density(items[t].v, area, best_v, best_area) && !better_density(best_v, best_area, items[t].v, area) && (y < best_y || (y == best_y && x < best_x)))) {
                        best_t = t;
                        best_rot = rot;
                        best_x = x;
                        best_y = y;
                        best_v = items[t].v;
                        best_area = area;
                    }
                }
            }
        }

        if (!anyFit || best_t == -1) break;

        int rw = items[best_t].w;
        int rh = items[best_t].h;
        if (best_rot == 1) { rw = items[best_t].h; rh = items[best_t].w; }

        // Place it
        sky.place(best_x, best_y, rw, rh);
        placements.push_back({items[best_t].id, best_x, best_y, best_rot});
        items[best_t].remain--;
        // Loop continues
    }

    // Output JSON
    cout << "{\n";
    cout << "  \"placements\": [";
    for (size_t i = 0; i < placements.size(); ++i) {
        auto &p = placements[i];
        cout << "\n    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i + 1 < placements.size()) cout << ",";
    }
    cout << "\n  ]\n";
    cout << "}\n";

    return 0;
}