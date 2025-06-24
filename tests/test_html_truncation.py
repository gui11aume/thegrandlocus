import pytest
from ..utils import HTMLStreamer, HTMLWordTruncator

# Tests for HTMLStreamer


@pytest.fixture
def streamer():
    """Returns a HTMLStreamer instance."""
    return HTMLStreamer()


def test_htmlstreamer_simple_html(streamer):
    """Test that basic HTML is processed correctly."""
    html = "<p>Hello, <b>world</b>!</p>"
    assert streamer.process(html) == html


@pytest.mark.parametrize(
    "html_input",
    [
        "<!DOCTYPE html>",
        "<!-- this is a comment -->",
        "&#123;",
        "&amp;",
        "&unknown;",
        "<?processing instruction>",
        # Combined case.
        "<!DOCTYPE html><!-- comment --><p>Testing&#123; &amp; &unknown; entities.</p><?pi instruction?>",
    ],
)
def test_htmlstreamer_handles_all_node_types(streamer, html_input):
    """Test that various HTML node types are handled correctly."""
    assert streamer.process(html_input) == html_input


@pytest.mark.parametrize("tag", ["br", "hr"])
def test_htmlstreamer_handles_self_closing_tags(streamer, tag):
    """Test that self-closing tags like <br/> are handled."""
    # Test with and without space before the slash
    for variant in (f"<{tag}/>", f"<{tag} />"):
        html = f"Hello{variant}world"
        processed = streamer.process(html)
        # The parser might output <tag> instead of <tag/>, which is fine.
        assert processed.lower() in (
            f"hello<{tag}>world",
            f"hello<{tag}/>world",
            f"hello<{tag} />world",
        )


@pytest.mark.parametrize(
    "html_input, expected_stack",
    [
        # Basic cases
        ("<div><p><span></span></p></div>", []),
        ("<div><p><span>", ["div", "p", "span"]),
        ("", []),
        # Malformed and edge cases
        ("</span></p></div>", []),  # Closing tags only
        ("<b><i></b></i>", ["b"]),  # Mismatched closing tag
        ("<a><b></a></b>", ["a"]),  # Out of order closing
        ("<a><b><c></b></c></a>", ["a", "b"]),  # Complex incorrect nesting
        # Mixed content
        ("<div><p></p><span></span></div>", []),  # Siblings
        ("<div><br><p></p></div>", []),  # With void element
    ],
)
def test_htmlstreamer_stack_management(streamer, html_input, expected_stack):
    """Test the tag stack is correctly managed across various scenarios."""
    streamer.process(html_input)
    assert streamer.stack == expected_stack


@pytest.mark.parametrize(
    "void_element_html",
    [
        "<area>",
        "<base>",
        "<br>",
        "<col>",
        "<command>",
        "<embed>",
        "<hr>",
        "<img>",
        "<input>",
        "<keygen>",
        "<link>",
        "<meta>",
        "<param>",
        "<source>",
        "<track>",
        "<wbr>",
        # Also test a case with multiple void elements together.
        '<img src="test.jpg"><br>',
    ],
)
def test_htmlstreamer_void_elements_not_in_stack(streamer, void_element_html):
    """Test that void elements are not added to the tag stack."""
    streamer.process(f"<div>{void_element_html}<p>text</p>")
    assert streamer.stack == ["div"]


@pytest.mark.parametrize(
    "html_input, expected_output",
    [
        # Basic case with multiple nested tags
        ("<div><p><span>", "<div><p><span></span></p></div>"),
        # No open tags, should be a no-op
        ("<div></div><p></p>", "<div></div><p></p>"),
        ("", ""),
        # Single open tag
        ("<div>", "<div></div>"),
        # With void elements that should be ignored by the closing logic
        ("<div><br><p>", "<div><br><p></p></div>"),
        # Malformed nesting
        ("<b><i></b>", "<b><i></b></i></b>"),
        ("<a><b></a></b>", "<a><b></a></b></a>"),
        # Tags with attributes
        (
            '<div class="main"><p id="intro">',
            '<div class="main"><p id="intro"></p></div>',
        ),
        (
            "<div class='main'><p id='intro'>",
            "<div class='main'><p id='intro'></p></div>",
        ),
    ],
)
def test_htmlstreamer_close_open_tags(streamer, html_input, expected_output):
    """Test that close_open_tags closes all tags in the correct order."""
    streamer.process(html_input)
    streamer.close_open_tags()
    result = streamer.out.getvalue()
    assert result == expected_output


@pytest.mark.parametrize(
    "html_input, expected_stack",
    [
        # Mismatched tags
        ("<b><i></b></i>", ["b"]),
        # Overlapping/interleaved tags
        ("<a><b></a></b>", ["a"]),
        ("<a><b><c></b></c>a>", ["a", "b"]),
        # Extraneous closing tags
        ("</a>", []),
        ("<div></p></div>", []),
        # Incomplete tags
        ("<div><p", ["div"]),
        ("<div></div", ["div"]),
        ("<div><p>Some text", ["div", "p"]),
        # Tags in attributes should not affect stack
        ('<div title="<b>"></div>', []),
    ],
)
def test_htmlstreamer_malformed_html(streamer, html_input, expected_stack):
    """Test stack management with various kinds of malformed HTML."""
    streamer.process(html_input)
    assert streamer.stack == expected_stack


@pytest.mark.parametrize(
    "html_input",
    [
        '<img src="image.jpg" alt=\'A "cat" in a hat\' title="it\'s a title">',
        '<a href="http://example.com?a=1&b=2">link</a>',
        '<p data-foo=\'{"key": "value"}\'>JSON data</p>',
        '<div title="a<b && c>d"></div>',
    ],
)
def test_htmlstreamer_attributes_with_special_chars(streamer, html_input):
    """Test attributes with quotes and other special characters."""
    assert streamer.process(html_input) == html_input


@pytest.mark.parametrize(
    "html_input",
    [
        "<style>body { color: red; }</style>",
        "<script>alert('hello & world');</script>",
        '<style type="text/css">.foo { content: "</div>"; }</style>',
        "<script> let a = '</script>'; </script>",
    ],
)
def test_htmlstreamer_script_and_style_content(streamer, html_input):
    """Test that script and style content is preserved."""
    assert streamer.process(html_input) == html_input


@pytest.mark.parametrize(
    "first_html, second_html, expected_stack",
    [
        ("<div>", "<p>", ["p"]),
        ("<div><p><b>", "<a>", ["a"]),
        ("<a><b></a>", "<i>", ["i"]),  # after malformed, state should reset
    ],
)
def test_htmlstreamer_process_state_isolation(
    streamer, first_html, second_html, expected_stack
):
    """Test that each call to process() is isolated."""
    streamer.process(first_html)
    streamer.process(second_html)
    assert streamer.stack == expected_stack
    assert streamer.out.getvalue() == second_html


@pytest.mark.parametrize(
    "attribute", ["disabled", "checked", "selected", "readonly", "required", "multiple"]
)
def test_htmlstreamer_attribute_without_value(streamer, attribute):
    """Test that attributes without values are handled."""
    html = f'<input type="checkbox" {attribute}>'
    processed = streamer.process(html)
    # The parser might add empty quotes.
    assert processed in (
        f'<input type="checkbox" {attribute}>',
        f'<input type="checkbox" {attribute}="">',
    )


@pytest.mark.parametrize(
    "unicode_string",
    [
        "Привет, мир!",  # Cyrillic.
        "你好世界",  # Chinese.
        "👋🌍",  # Emoji.
        "مرحبا بالعالم",  # Arabic.
    ],
)
def test_htmlstreamer_unicode_handling(streamer, unicode_string):
    """Test that unicode characters in content and attributes are handled."""
    html_content = f"<p>{unicode_string}</p>"
    assert streamer.process(html_content) == html_content

    html_attr = f'<div title="{unicode_string}"></div>'
    assert streamer.process(html_attr) == html_attr


# Tests for HTMLWordTruncator.


@pytest.mark.parametrize(
    "html_input, word_limit, expected_output",
    [
        # No truncation needed.
        ("Hello world", 5, "Hello world"),
        (
            "<p>Hello world, this is a test.</p>",
            10,
            "<p>Hello world, this is a test.</p>",
        ),
        ("No tags here", None, "No tags here"),
        # Simple text truncation.
        ("one two three four", 2, "one two__TRUNCATION_MARKER_"),
        (
            "A sentence with several words.",
            4,
            "A sentence with several__TRUNCATION_MARKER_",
        ),
        ("one two three four", 0, "__TRUNCATION_MARKER_"),
        # Truncation with HTML.
        (
            "<p>This is <b>some bold</b> text.</p>",
            4,
            "<p>This is <b>some bold__TRUNCATION_MARKER_</b></p>",
        ),
        (
            "<span><a>Nested link to truncate</a></span>",
            3,
            "<span><a>Nested link to__TRUNCATION_MARKER_</a></span>",
        ),
        (
            "<div>One two <img> three four</div>",
            3,
            "<div>One two <img> three__TRUNCATION_MARKER_</div>",
        ),
        ("Stop<p>before the next word.</p>", 1, "Stop__TRUNCATION_MARKER_"),
        (
            "Truncate right after a tag <b>boldly</b>.",
            6,
            "Truncate right after a tag <b>boldly__TRUNCATION_MARKER_</b>",
        ),
        # Edge cases.
        ("one-two three", 1, "one-two__TRUNCATION_MARKER_"),  # Test hyphenated words.
        ("", 5, ""),
        ("   leading spaces", 2, "   leading spaces"),
        ("trailing spaces   ", 2, "trailing spaces   "),
        ("<p></p><b></b>", 5, "<p></p><b></b>"),  # No words.
    ],
)
def test_html_word_truncator(html_input, word_limit, expected_output):
    """Test HTMLWordTruncator with various inputs."""
    truncator = HTMLWordTruncator(max_words=word_limit)
    assert truncator.process(html_input) == expected_output


@pytest.mark.parametrize(
    "html_input, word_limit, expected_output",
    [
        # Punctuation
        ("one, two, three.", 2, "one, two__TRUNCATION_MARKER_"),
        (
            "words-with-hyphens are-counted-as-one",
            1,
            "words-with-hyphens__TRUNCATION_MARKER_",
        ),
        # Multiple spaces and newlines
        ("one \n two \t three", 2, "one \n two__TRUNCATION_MARKER_"),
        # Truncation at tag boundaries
        ("one <b>two</b> three", 2, "one <b>two__TRUNCATION_MARKER_</b>"),
        # HTML comments and entities
        ("one <!-- comment --> two", 2, "one <!-- comment --> two"),
        ("one &amp; two", 2, "one &amp; two"),  # entities are not words
        ("one &#123; two", 2, "one &#123; two"),
        # Unicode characters
        ("Привет мир, как дела?", 2, "Привет мир__TRUNCATION_MARKER_"),
        # Mixed content
        (
            "<p>First word.</p> <div>Second word.</div>",
            2,
            "<p>First word.__TRUNCATION_MARKER_</p>",
        ),
        (
            " leading space and <b>tags</b> then text",
            4,
            " leading space and <b>tags__TRUNCATION_MARKER_</b>",
        ),
        # Words with apostrophes (known issue with current regex)
        ("it's a test", 2, "it's__TRUNCATION_MARKER_"),
        # No words, just tags and spaces
        (" <p> <i> </i> </p> ", 5, " <p> <i> </i> </p> "),
    ],
)
def test_html_word_truncator_corner_cases(html_input, word_limit, expected_output):
    """Test HTMLWordTruncator with additional corner cases."""
    truncator = HTMLWordTruncator(max_words=word_limit)
    assert truncator.process(html_input) == expected_output


@pytest.mark.parametrize(
    "html_input, word_limit, expected_output",
    [
        # Truncation before a tag, preserving the space.
        ("one <b>two</b> three", 1, "one __TRUNCATION_MARKER_"),
        # Multiple spaces.
        ("word1  <i>word2</i>", 1, "word1  __TRUNCATION_MARKER_"),
        # Different tag.
        ("word1 <strong>word2</strong>", 1, "word1 __TRUNCATION_MARKER_"),
        # Another tag.
        ("words <span>and words</span>", 1, "words __TRUNCATION_MARKER_"),
        # More words before truncation.
        ("a b c <a>d e f</a>", 3, "a b c __TRUNCATION_MARKER_"),
        # More words and spaces.
        ("a b c  <a>d e f</a>", 3, "a b c  __TRUNCATION_MARKER_"),
    ],
)
def test_html_word_truncator_space_before_tag(html_input, word_limit, expected_output):
    """Test truncation where whitespace is preserved before a tag."""
    truncator = HTMLWordTruncator(max_words=word_limit)
    assert truncator.process(html_input) == expected_output


def test_html_word_truncator_custom_end():
    """Test HTMLWordTruncator with a custom end string."""
    truncator = HTMLWordTruncator(max_words=3, end=" [read more]")
    html = "This is some sample text."
    expected = "This is some [read more]"
    assert truncator.process(html) == expected


def test_html_word_truncator_complex_nesting():
    """Test truncation with deeply nested tags that must all be closed."""
    html = "<div><p>Here is <em>some <i>very important</i> text</em> to test.</p></div>"
    truncator = HTMLWordTruncator(max_words=5)
    expected = "<div><p>Here is <em>some <i>very important__TRUNCATION_MARKER_</i></em></p></div>"
    assert truncator.process(html) == expected
