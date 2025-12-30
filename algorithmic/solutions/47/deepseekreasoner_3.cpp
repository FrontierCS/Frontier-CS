#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <map>
#include <utility>
#include <cstdint>
#include <cctype>
#include <cstring>

using namespace std;

// ----------------------------------------------------------------------
// Simple JSON parser (only for the needed structure)
// ----------------------------------------------------------------------
enum JsonType { OBJECT, ARRAY, STRING, NUMBER, BOOL, NUL };

struct JsonNode {
    JsonType type;
    std::map<std::string, JsonNode> obj;
    std::vector<JsonNode> arr;
    std::string str;
    long long num;
    bool b;

    JsonNode() : type(NUL) {}
    JsonNode(JsonType t) : type(t) {}
    JsonNode(const std::string& s) : type(STRING), str(s) {}
    JsonNode(long long n) : type(NUMBER), num(n) {}
    JsonNode(bool bl) : type(BOOL), b(bl) {}
};

void skip_ws(const std::string& s, size_t& i) {
    while (i < s.size() && isspace(static_cast<unsigned char>(s[i]))) ++i;
}

JsonNode parse_json(const std::string& s, size_t& i) {
    skip_ws(s, i);
    if (i >= s.size()) return JsonNode(NUL);
    char c = s[i];
    if (c == '{') {
        JsonNode node(OBJECT);
        ++i; // skip '{'
        while (i < s.size()) {
            skip_ws(s, i);
            if (s[i] == '}') { ++i; break; }
            // parse key (string)
            if (s[i] != '"') return JsonNode(NUL);
            ++i;
            size_t start = i;
            while (i < s.size() && s[i] != '"') ++i;
            if (i >= s.size()) return JsonNode(NUL);
            std::string key = s.substr(start, i - start);
            ++i; // skip '"'
            skip_ws(s, i);
            if (s[i] != ':') return JsonNode(NUL);
            ++i; // skip ':'
            JsonNode val = parse_json(s, i);
            node.obj[key] = val;
            skip_ws(s, i);
            if (s[i] == '}') { ++i; break; }
            if (s[i] != ',') return JsonNode(NUL);
            ++i; // skip ','
        }
        return node;
    } else if (c == '[') {
        JsonNode node(ARRAY);
        ++i; // skip '['
        while (i < s.size()) {
            skip_ws(s, i);
            if (s[i] == ']') { ++i; break; }
            JsonNode val = parse_json(s, i);
            node.arr.push_back(val);
            skip_ws(s, i);
            if (s[i] == ']') { ++i; break; }
            if (s[i] != ',') return JsonNode(NUL);
            ++i; // skip ','
        }
        return node;
    } else if (c == '"') {
        ++i;
        size_t start = i;
        while (i < s.size() && s[i] != '"') ++i;
        if (i >= s.size()) return JsonNode(NUL);
        std::string str = s.substr(start, i - start);
        ++i; // skip '"'
        return JsonNode(str);
    } else if (isdigit(c) || c == '-') {
        size_t start = i;
        if (c == '-') ++i;
        while (i < s.size() && isdigit(s[i])) ++i;
        if (i < s.size() && s[i] == '.') ++i; // we don't handle floats, but just in case
        while (i < s.size() && isdigit(s[i])) ++i;
        std::string numstr = s.substr(start, i - start);
        long long num = stoll(numstr);
        return JsonNode(num);
    } else if (c == 't' && s.substr(i, 4) == "true") {
        i += 4;
        return JsonNode(true);
    } else if (c == 'f' && s.substr(i, 5) == "false") {
        i += 5;
        return JsonNode(false);
    } else if (c == 'n' && s.substr(i, 4) == "null") {
        i += 4;
        return JsonNode(NUL);
    }
    return JsonNode(NUL);
}

JsonNode parse_input() {
    std::string input, line;
    while (getline(std::cin, line)) input += line;
    size_t pos = 0;
    return parse_json(input, pos);
}

// ----------------------------------------------------------------------
// Packing structures
// ----------------------------------------------------------------------
struct Type {
    std::string id;
    int w, h, v, limit;
    int remaining; // during packing
};

struct Shape {
    const Type* type;
    int width, height, profit;
    int rot; // 0 or 1
};

struct Placement {
    std::string type;
    int x, y, rot;
};

struct Shelf {
    int height;      // fixed shelf height
    int used_width;  // used width in this shelf
};

// ----------------------------------------------------------------------
// First-Fit Decreasing Height (FFDH) packing
// ----------------------------------------------------------------------
int pack_ffdh(const std::vector<Shape>& shapes, int W, int H,
              std::vector<Placement>& placements) {
    placements.clear();
    std::vector<Shelf> shelves;
    int total_height = 0;
    int profit = 0;

    // We need to work on a copy of remaining counts because shapes share types.
    // We'll use the original remaining from the types, but we need to reset after each attempt.
    // Instead, we'll pass shapes with remaining counts as mutable? Actually we'll store remaining in Type.
    // So we'll assume shapes are sorted and we iterate.

    for (const Shape& sh : shapes) {
        int* rem = &(const_cast<Type*>(sh.type)->remaining); // we need to modify
        while (*rem > 0) {
            bool placed = false;
            // try existing shelves
            int y = 0;
            for (size_t i = 0; i < shelves.size(); ++i) {
                if (sh.height <= shelves[i].height &&
                    shelves[i].used_width + sh.width <= W) {
                    placements.push_back({sh.type->id, shelves[i].used_width, y, sh.rot});
                    shelves[i].used_width += sh.width;
                    profit += sh.profit;
                    --(*rem);
                    placed = true;
                    break;
                }
                y += shelves[i].height;
            }
            if (placed) continue;
            // create new shelf
            if (total_height + sh.height <= H) {
                placements.push_back({sh.type->id, 0, total_height, sh.rot});
                shelves.push_back({sh.height, sh.width});
                profit += sh.profit;
                total_height += sh.height;
                --(*rem);
                placed = true;
            }
            if (!placed) break; // cannot place this shape anymore
        }
    }
    return profit;
}

// ----------------------------------------------------------------------
// Comparison functions for sorting shapes
// ----------------------------------------------------------------------
bool by_height_desc(const Shape& a, const Shape& b) {
    if (a.height != b.height) return a.height > b.height;
    if (a.width != b.width) return a.width > b.width;
    return a.profit > b.profit;
}

bool by_width_desc(const Shape& a, const Shape& b) {
    if (a.width != b.width) return a.width > b.width;
    if (a.height != b.height) return a.height > b.height;
    return a.profit > b.profit;
}

bool by_area_desc(const Shape& a, const Shape& b) {
    int area_a = a.width * a.height;
    int area_b = b.width * b.height;
    if (area_a != area_b) return area_a > area_b;
    return a.profit > b.profit;
}

bool by_profit_density_desc(const Shape& a, const Shape& b) {
    double dens_a = static_cast<double>(a.profit) / (a.width * a.height);
    double dens_b = static_cast<double>(b.profit) / (b.width * b.height);
    if (fabs(dens_a - dens_b) > 1e-9) return dens_a > dens_b;
    return by_area_desc(a, b);
}

bool by_profit_desc(const Shape& a, const Shape& b) {
    if (a.profit != b.profit) return a.profit > b.profit;
    return by_area_desc(a, b);
}

bool by_height_desc_then_density(const Shape& a, const Shape& b) {
    if (a.height != b.height) return a.height > b.height;
    return by_profit_density_desc(a, b);
}

bool by_width_desc_then_density(const Shape& a, const Shape& b) {
    if (a.width != b.width) return a.width > b.width;
    return by_profit_density_desc(a, b);
}

bool by_height_asc(const Shape& a, const Shape& b) {
    if (a.height != b.height) return a.height < b.height;
    if (a.width != b.width) return a.width < b.width;
    return a.profit > b.profit;
}

bool by_width_asc(const Shape& a, const Shape& b) {
    if (a.width != b.width) return a.width < b.width;
    if (a.height != b.height) return a.height < b.height;
    return a.profit > b.profit;
}

bool by_area_asc(const Shape& a, const Shape& b) {
    int area_a = a.width * a.height;
    int area_b = b.width * b.height;
    if (area_a != area_b) return area_a < area_b;
    return a.profit > b.profit;
}

// ----------------------------------------------------------------------
// Main solver
// ----------------------------------------------------------------------
int main() {
    // Seed random number generator
    srand(static_cast<unsigned>(time(nullptr)));

    // Parse input
    JsonNode root = parse_input();
    if (root.type != OBJECT) return 1;

    int W = root.obj["bin"].obj["W"].num;
    int H = root.obj["bin"].obj["H"].num;
    bool allow_rotate = root.obj["bin"].obj["allow_rotate"].b;

    std::vector<Type> types;
    for (const JsonNode& item : root.obj["items"].arr) {
        Type t;
        t.id = item.obj["type"].str;
        t.w = item.obj["w"].num;
        t.h = item.obj["h"].num;
        t.v = item.obj["v"].num;
        t.limit = item.obj["limit"].num;
        t.remaining = t.limit; // will be reset before each packing attempt
        types.push_back(t);
    }

    // Generate shapes (considering rotation)
    std::vector<Shape> base_shapes;
    for (const Type& t : types) {
        // original orientation
        if (t.w <= W && t.h <= H) {
            base_shapes.push_back({&t, t.w, t.h, t.v, 0});
        }
        // rotated orientation (if allowed and fits)
        if (allow_rotate) {
            if (t.h <= W && t.w <= H) {
                base_shapes.push_back({&t, t.h, t.w, t.v, 1});
            }
        }
    }

    // Prepare list of sorting functions to try
    typedef bool (*CompFunc)(const Shape&, const Shape&);
    std::vector<std::pair<CompFunc, std::string>> sorters = {
        {by_height_desc, "height_desc"},
        {by_width_desc, "width_desc"},
        {by_area_desc, "area_desc"},
        {by_profit_density_desc, "profit_density_desc"},
        {by_profit_desc, "profit_desc"},
        {by_height_desc_then_density, "height_desc_then_density"},
        {by_width_desc_then_density, "width_desc_then_density"},
        {by_height_asc, "height_asc"},
        {by_width_asc, "width_asc"},
        {by_area_asc, "area_asc"}
    };

    int best_profit = -1;
    std::vector<Placement> best_placements;

    // Try each deterministic sorter
    for (auto& sorter : sorters) {
        // Reset remaining counts
        for (Type& t : types) t.remaining = t.limit;
        // Sort shapes
        std::vector<Shape> shapes = base_shapes;
        std::sort(shapes.begin(), shapes.end(), sorter.first);
        // Pack
        std::vector<Placement> placements;
        int profit = pack_ffdh(shapes, W, H, placements);
        if (profit > best_profit) {
            best_profit = profit;
            best_placements = placements;
        }
    }

    // Try random shuffles (multiple times)
    const int RANDOM_TRIALS = 100;
    for (int trial = 0; trial < RANDOM_TRIALS; ++trial) {
        // Reset remaining counts
        for (Type& t : types) t.remaining = t.limit;
        // Random shuffle
        std::vector<Shape> shapes = base_shapes;
        std::random_shuffle(shapes.begin(), shapes.end());
        // Pack
        std::vector<Placement> placements;
        int profit = pack_ffdh(shapes, W, H, placements);
        if (profit > best_profit) {
            best_profit = profit;
            best_placements = placements;
        }
    }

    // Output best packing found
    std::cout << "{\"placements\":[";
    for (size_t i = 0; i < best_placements.size(); ++i) {
        if (i > 0) std::cout << ",";
        std::cout << "{\"type\":\"" << best_placements[i].type
                  << "\",\"x\":" << best_placements[i].x
                  << ",\"y\":" << best_placements[i].y
                  << ",\"rot\":" << best_placements[i].rot << "}";
    }
    std::cout << "]}" << std::endl;

    return 0;
}